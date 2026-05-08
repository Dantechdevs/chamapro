from .models import Membership

def user_subscription(request):
    if request.user.is_authenticated:
        try:
            sub = request.user.subscription
        except Exception:
            sub = None
        return {'user_subscription': sub}
    return {'user_subscription': None}


def active_chama(request):
    if not request.user.is_authenticated:
        return {}

    active_chama_id = request.session.get('active_chama_id')
    membership = None

    if active_chama_id:
        membership = Membership.objects.filter(
            user=request.user,
            chama_id=active_chama_id,
            active=True
        ).select_related('chama').first()

    if not membership:
        membership = Membership.objects.filter(
            user=request.user,
            active=True
        ).select_related('chama').first()

    return {
        'chama': membership.chama if membership else None,
        'my_membership': membership,
    }