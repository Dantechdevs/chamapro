def user_subscription(request):
    if request.user.is_authenticated:
        try:
            sub = request.user.subscription
        except Exception:
            sub = None
        return {'user_subscription': sub}
    return {'user_subscription': None}