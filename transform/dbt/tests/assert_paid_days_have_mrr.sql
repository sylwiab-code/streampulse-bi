-- Every paid subscription-day carries a positive MRR (also during payment retries).
select
    date_day,
    subscription_id,
    mrr_local
from {{ ref('fct_subscription_daily') }}
where subscription_status = 'paid' and (mrr_local is null or mrr_local <= 0)
