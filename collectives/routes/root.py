from flask import redirect, url_for, Blueprint
from flask import current_app, render_template

blueprint = Blueprint('root', __name__)

@blueprint.route('/')
@blueprint.route('/index')
@blueprint.route('/list')
def index():
    return redirect(url_for('event.index'))

@blueprint.route('/legal')
def legal():
    return render_template('legal.html',
                           conf=current_app.config)
