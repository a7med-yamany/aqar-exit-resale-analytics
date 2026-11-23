"""AqarExit Resale Analytics pages over the verified SQL layer."""
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse
from functools import wraps

import pandas as pd
import plotly.graph_objects as go
import pymysql
import streamlit as st

import app_service
from ui_helpers import LABELS,amount,csv_download,filter_properties,labeled_rows


@st.cache_data(ttl=300,max_entries=128,show_spinner=False)
def data(method,*args):
    return app_service.read(method,*args)


def recoverable_fragment(func):
    @wraps(func)
    def wrapped(*args,**kwargs):
        try:
            return func(*args,**kwargs)
        except (pymysql.Error,OSError,RuntimeError,ValueError):
            st.error('We couldn’t load this section. Please try again.')
            if st.button('Retry section',key='retry_'+func.__name__):
                data.clear()
                st.rerun()
    return wrapped


def heading(title,description):
    st.title(title)
    st.caption(description)


def frame(rows,columns,filename=None):
    if not rows:
        st.info('No results match your selection. Try a different area or fewer filters.')
        return
    displayed=labeled_rows(rows,columns)
    df=pd.DataFrame(displayed)
    # Conversion is display-only; query arithmetic retains exact DECIMAL values.
    for key in df:
        if any(isinstance(v,Decimal) for v in df[key]):
            df[key]=df[key].map(lambda v:float(v) if v is not None else None)
    configs={}
    for key in columns:
        label=LABELS.get(key,key)
        if key.endswith('year') or key=='rank_in_type':
            configs[label]=st.column_config.NumberColumn(format='%d')
        elif 'EGP' in label or 'm²' in label or '%' in label:
            configs[label]=st.column_config.NumberColumn(
                format='%,.2f' if 'm²' in label or '%' in label else '%,.0f')
        elif key=='avg_contract_age_years':
            configs[label]=st.column_config.NumberColumn(format='%.1f')
    st.dataframe(df,hide_index=True,width='stretch',column_config=configs,height='auto')
    if filename:
        st.download_button('Download results',csv_download(displayed),file_name=filename,
                           mime='text/csv',icon=':material/download:',on_click='ignore')


def area_picker(options,key,allow_all=False):
    names={r['area_ID']:r['area_name'] for r in options['areas']}
    ids=list(names)
    if allow_all:
        ids=[None]+ids
    default=ids.index(11) if 11 in ids and not allow_all else 0
    return st.selectbox('Area',ids,index=default,key=key,
        format_func=lambda i:'All areas' if i is None else names[i])


def project_picker(options,key):
    areas={r['area_ID']:r['area_name'] for r in options['areas']}
    names={r['project_ID']:f"{r['project_name']} · {areas.get(r['area_ID'],'')} · #{r['project_ID']}" for r in options['projects']}
    return st.selectbox('Development project',list(names),key=key,format_func=names.get)


def definitions():
    with st.expander('How these figures are calculated'):
        st.markdown('**Resale price** is the seller’s required amount plus the remaining developer balance. '
                    '**Cash now including fees** is shown separately. **Price per m²** is resale price divided by property area; '
                    'group averages give each known listing equal weight. **Gain/discount** uses the source’s reported '
                    'gain, which accounts for immediate fees. Unknown values are excluded from averages.')
        st.markdown('**Installments** are normalized to monthly/annual amounts, preferring a reported annual amount. '
                    '**Contract age** uses the current year and excludes unknown or future years. '
                    'Shared projects count once for each participating developer.')


METRICS={'Resale inventory':('inventory','resale_inventory','Listings'),
         'Resale amount':('resale_amount','resale_amount','Resale amount (EGP)'),
         'Average gain':('gain','avg_gain_over_market','Average gain (EGP)')}


def ranking_chart(rows,value,label,name='project_name'):
    known=[r for r in rows if r.get(value) is not None]
    if not known:
        st.info('No known values are available for this ranking.')
        return
    labels=[str(r[name]) for r in known]
    short=[(n[:33]+'…' if len(n)>34 else n)+f'  #{i+1}' for i,n in enumerate(labels)]
    fig=go.Figure(go.Bar(x=[float(r[value]) for r in known],y=short,orientation='h',
        marker_color='#007e78',customdata=labels,
        hovertemplate='%{customdata}<br>'+label+': %{x:,.0f}<extra></extra>'))
    fig.update_layout(height=max(280,len(known)*36+65),margin=dict(l=0,r=15,t=8,b=35),
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Arial, sans-serif',size=12,color='#172c3d'),
        xaxis=dict(title=label,gridcolor='#e5eaed',zeroline=False),
        yaxis=dict(autorange='reversed',title=None),showlegend=False)
    st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})


@st.fragment
@recoverable_fragment
def rankings(options,key):
    left,right=st.columns([2,1])
    with left:
        metric=st.segmented_control('Rank projects by',list(METRICS),default='Resale inventory',key=key+'_metric',selection_mode='single')
    types=[r['type'] for r in options['property_types']]
    with right:
        default=next((types.index(t) for t in ['شقة','Apartment'] if t in types),0)
        property_type=st.selectbox('Property type',types,index=default,key=key+'_type')
    metric=metric or 'Resale inventory'
    code,value,label=METRICS[metric]
    rows=[r for r in data('top_projects',code) if r['property_type']==property_type]
    ranking_chart(rows,value,label)
    frame(rows,['rank_in_type','project_name','property_type','resale_inventory','priced_listings',
                'resale_amount','avg_gain_over_market','gain_known_listings'],key+'-rankings.csv')
    st.caption('Up to ten projects for the selected property type. Average gain uses known values; ties use project reference.')


def overview():
    heading('A clearer view of resale.','Explore inventory, compare developments and understand the Egyptian resale market.')
    with st.spinner('Loading market overview…'):
        options=data('lookup_options')
        counts=data('overview_counts')
    for col,key,label in zip(st.columns(3),['listings','projects','developers'],['Resale listings','Development projects','Developers']):
        col.metric(label,amount(counts[key]))
    st.write('')
    with st.container(border=True):
        st.subheader('Leading developments')
        rankings(options,'overview')
    st.write('')
    st.subheader('From market view to property detail')
    st.caption('Open Property explorer to compare areas, prices, amenities and contract years. '
               'Projects & reviews brings together unit-type statistics and community feedback.')
    definitions()


PROPERTY_COLUMNS=['project_name','area_name','property_type','area_sqm','No_bedrooms',
                  'resale_price','resale_price_per_sqm','area_type_avg_price_per_sqm','down_payment',
                  'cash_required_now','remaining_balance','gain_over_current_value','contract_year','listing_ID']


@st.fragment
@recoverable_fragment
def listing_detail(rows):
    labels={r['listing_ID']:f"{r.get('project_name') or 'Standalone property'} · {r['property_type']} · {amount(r['resale_price'])} EGP · {r['listing_ID'][:8]}" for r in rows}
    listing=st.selectbox('Inspect a listing',list(labels),format_func=labels.get,index=None,
                         placeholder='Choose a listing to see payment details and amenities',key='listing_detail')
    if listing is None:
        return
    row=data('listing_details',listing)
    if row is None:
        st.info('This listing is no longer available. Refresh the results.')
        return
    with st.container(border=True):
        st.subheader('Property details')
        st.text(row.get('project_name') or 'Standalone property')
        st.caption(f"{row['area_name']} · {row['property_type']} · {amount(row['area_sqm'],2)} m²")
        for col,key,label in zip(st.columns(3),['resale_price','down_payment','remaining_balance'],
                                  ['Resale price · EGP','Required down payment · EGP','Remaining balance · EGP']):
            col.metric(label,amount(row[key]))
        frame([row],['cash_required_now','market_price','gain_over_current_value','contract_year','No_bedrooms','No_bathrooms'])
        st.write('Amenities')
        st.text(' · '.join(row['amenities']) or 'Not available')
        if row.get('property_location'):
            st.write('Property location')
            st.text(row['property_location'])
        if row.get('description'):
            with st.expander('Read full listing description'):
                st.text(row['description'])
        uri=urlparse(row.get('source_URL') or '')
        if uri.scheme=='https' and uri.hostname in {'aqarexit.com','www.aqarexit.com'}:
            st.link_button('View original listing',row['source_URL'],icon=':material/open_in_new:')


def explorer():
    heading('Explore resale properties.','Find listings by area, budget and amenities, with financial details in one place.')
    options=data('lookup_options')
    with st.form('property_search'):
        a,b,c=st.columns([1.3,1,1])
        with a: area=area_picker(options,'explorer_area')
        with b:
            typ=st.selectbox('Property type',[None]+[r['type'] for r in options['property_types']],
                format_func=lambda v:v or 'All property types',key='explorer_type')
        with c:
            year=st.selectbox('Contract year',[None]+[r['contract_year'] for r in options['contract_years']],
                format_func=lambda v:str(v) if v else 'All contract years',key='explorer_year')
        amenities=st.multiselect('Required amenities',[r['amenities'] for r in options['amenities']],
            help='A listing must have every selected amenity.',key='explorer_amenities')
        a,b,c=st.columns([1,1,1])
        with a:
            budget=st.checkbox('Filter by resale price',key='explorer_budget')
        with b: low=st.number_input('Minimum price (EGP)',min_value=0,value=0,step=100000,key='explorer_min')
        with c: high=st.number_input('Maximum price (EGP)',min_value=0,value=10000000,step=100000,key='explorer_max')
        submitted=st.form_submit_button('Search properties',type='primary',icon=':material/search:')
    if budget and low>high:
        st.error('Minimum price must not exceed maximum price.')
        return
    with st.spinner('Finding matching properties…'):
        rows=data('area_properties',area)
        rows=filter_properties(rows,typ,year,low if budget else None,high if budget else None,amenities)
    st.subheader(f'{len(rows):,} matching listings')
    st.caption('Area/type averages describe all listings of that type in the selected area, before your filters. '
               'Price bounds include both endpoints. Listings with unknown prices are excluded only when a price filter is applied.')
    frame(rows,PROPERTY_COLUMNS,'aqar-exit-properties.csv')
    if rows:
        listing_detail(rows)
    definitions()


def write_error(exc,context='profile'):
    if isinstance(exc,pymysql.IntegrityError):
        if exc.args[0]==1062:
            st.error('You already reviewed this development. Each profile can publish one review per development.'
                     if context=='review' else 'A profile with this email already exists. Use your registered email to publish reviews.')
        elif context=='review':
            st.error('Your profile or the development is no longer available. Check your registered email and refresh the project list.')
        else:
            st.error('We couldn’t save this entry. Check that the profile, project and areas exist, then try again.')
    elif isinstance(exc,ValueError):
        st.error(str(exc))
    else:
        st.error('We couldn’t confirm that this entry was saved. Check the project reviews or profile before trying again.')


def projects():
    heading('Projects, with context.','Explore development locations, compare unit types and read community reviews.')
    options=data('lookup_options')
    project=project_picker(options,'project_id')
    stats=data('project_statistics',project)
    if not stats:
        st.info('This project was not found. Refresh the data and choose another project.')
        return
    with st.container(border=True):
        st.subheader('Development overview')
        st.text(stats[0]['project_name'])
        st.caption(stats[0]['area_name'])
        st.write('Location')
        st.text(stats[0]['location_detail'] or 'Location details are not available for this development.')
        frame(stats,['property_type','listing_count','priced_listings','avg_price_per_sqm'])
    st.subheader('Community reviews')
    reviews=data('project_reviews',project)
    st.caption(f'{len(reviews):,} reviews. Ratings are on a scale of 1–10.')
    if reviews:
        page=st.number_input('Review page',min_value=1,max_value=max(1,(len(reviews)+9)//10),value=1,step=1,key=f'review_page_{project}')
        for review in reviews[(page-1)*10:page*10]:
            with st.container(border=True):
                left,right=st.columns([5,1])
                left.text(review['username'])
                right.write(f"**{review['rating_1_to_10']} / 10**")
                st.text(review['text_review'])
    else:
        st.info('No reviews yet. Share the first review of this development.')
    with st.expander('Write a review'):
        st.caption('Use the email of your registered profile. Each profile can review a development once. '
                   'If you haven’t registered yet, open Register profile first.')
        with st.form('review_form',clear_on_submit=False):
            email=st.text_input('Registered email',value=st.session_state.get('profile_email',''),max_chars=254)
            rating=st.slider('Rating',min_value=1,max_value=10,value=8)
            text=st.text_area('Your review',max_chars=12000)
            submitted=st.form_submit_button('Publish review',type='primary')
        if submitted:
            try:
                app_service.review(project,email,rating,text)
            except (ValueError,pymysql.Error) as exc:
                write_error(exc,'review')
            else:
                data.clear('project_reviews',project)
                st.session_state['review_saved']=True
                st.rerun()
    if st.session_state.pop('review_saved',False):
        st.success('Your review has been published.')
    definitions()


def developers():
    heading('Compare the developers.','The five most active developers by resale listing count.')
    rows=data('top_developers')
    with st.container(border=True):
        st.subheader('Resale inventory leaders')
        ranking_chart(rows,'listing_count','Listings','dev_name')
    frame(rows,['dev_name','listing_count','priced_listings','avg_price_per_sqm',
                'avg_required_down_payment','avg_cash_required_now','avg_gain_over_market',
                'total_gain_over_market'],'aqar-exit-developers.csv')
    st.caption('A shared development contributes its listings to each participating developer. '
               'Standalone properties are attributed to their directly recorded developer.')
    definitions()


def reports():
    heading('Ask a better market question.','Compare developments using consistent resale and payment measures.')
    options=data('lookup_options')
    tab1,tab2=st.tabs(['Market summary','Project rankings'],key='report_tab',on_change='rerun')
    if tab1.open:
      with tab1:
        a,b=st.columns(2)
        with a: area=area_picker(options,'summary_area',True)
        summaries=data('market_summary')
        selected=[r for r in summaries if area is None or r['area_ID']==area]
        with b:
            project_names={r['project_ID']:r['project_name'] or 'Standalone properties' for r in selected}
            project=st.selectbox('Development',["all"]+list(project_names),key='summary_project',
                format_func=lambda v:'All developments' if v=='all' else project_names[v])
        if project!='all':
            selected=[r for r in selected if r['project_ID']==project]
        st.subheader('Area & development summary')
        st.caption(f'{len(selected):,} groups · prices in EGP · installments normalized to monthly and annual amounts')
        # Give the NULL project group an honest display label without changing IDs.
        selected=[{**r,'project_name':r['project_name'] or 'Standalone properties'} for r in selected]
        frame(selected,['area_name','project_name','property_count','listing_count','avg_resale_price',
            'avg_price_per_sqm','avg_monthly_installment','avg_annual_installment',
            'avg_down_payment','avg_cash_required_now','avg_discount_amount','avg_discount_pct',
            'avg_contract_age_years','avg_market_price'],'aqar-exit-market-summary.csv')
        with st.expander('Coverage of the averages'):
            frame(selected,['area_name','project_name','listing_count','installment_known_listings',
                'down_payment_known_listings','discount_known_listings','discount_pct_known_listings',
                'contract_age_known_listings','market_price_known_listings'])
    if tab2.open:
      with tab2:
        rankings(options,'reports')
    definitions()


def registration():
    heading('Keep your interests in focus.','Create a profile to share development reviews and record the areas you follow.')
    options=data('lookup_options')
    areas={r['area_ID']:r['area_name'] for r in options['areas']}
    with st.form('registration',clear_on_submit=False):
        left,right=st.columns(2)
        with left:
            email=st.text_input('Email address',max_chars=254,placeholder='you@example.com')
            birthdate=st.date_input('Birthdate',value=date(2000,1,1),min_value=date(1900,1,1),max_value=date.today())
        with right:
            username=st.text_input('Username',max_chars=100,placeholder='How your name appears on reviews')
            gender=st.selectbox('Gender (optional)',['Prefer not to say','Female','Male','Other'])
        focus=st.multiselect('Areas of interest',list(areas),format_func=areas.get,
                             help='Choose at least one area.')
        st.caption('Your email identifies your profile and is not displayed with public reviews. '
                   'Age is derived from birthdate. All fields except gender are required.')
        submitted=st.form_submit_button('Create profile',type='primary')
    if submitted:
        try:
            address=app_service.register(email,username,None if gender=='Prefer not to say' else gender,birthdate,focus)
        except (ValueError,pymysql.Error) as exc:
            write_error(exc)
        else:
            st.session_state['profile_email']=address
            st.success('Your profile has been created. Open Projects & reviews to share your experience.')
