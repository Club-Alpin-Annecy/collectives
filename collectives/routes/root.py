from flask import redirect, url_for, Blueprint

blueprint = Blueprint('root', __name__)

@blueprint.route('/')
@blueprint.route('/index')
@blueprint.route('/list')
def index():
    return redirect(url_for('event.index'))