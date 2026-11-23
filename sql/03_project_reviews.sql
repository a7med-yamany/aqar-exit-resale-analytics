SELECT r.project_ID, r.user_email, u.username, r.rating_1_to_10, r.text_review
FROM review r JOIN `user` u ON u.user_email = r.user_email
WHERE r.project_ID = %s
ORDER BY r.user_email
