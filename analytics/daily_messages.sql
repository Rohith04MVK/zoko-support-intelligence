-- UTC daily volume; duplicates additionally guarded by message ID.
SELECT
    toDate(timestamp) AS day,
    count(DISTINCT properties.message_id) AS messages
FROM events
WHERE event = 'message_recorded'
  AND properties.source = 'support_intelligence'
GROUP BY day
ORDER BY day ASC
