from flask import Blueprint, render_template, current_app, request, flash, \
    url_for, redirect, session, abort, g
from flask_login import login_user, logout_user, current_user, login_required
from frontend.form import LoginForm
from api.views import get_toplogy
from user import User
from extensions import cache
from node import Indb_func
import uuid
import hashlib
import requests
from utils import github
from flask_socketio import (
    send,
    SocketIO,
    emit,
    disconnect,
    join_room
)

frontend = Blueprint('frontend', __name__, template_folder='../templates')

#frontend = Blueprint('frontend', __name__)
'''
### DOC ###

frontend pages 
/index

'''


@frontend.before_request
def frontend_before_request():
    current_app.logger.info(str(current_user.name) + "@uid:" + str(current_user.id) +
                            " @session:" + session.session_id + " @request_url:" + request.url + " @IP:" + ret_ip())
    g.user = current_user


@frontend.teardown_request
def frontend_teardown_request(extensions):
    pass


@frontend.route('/testcache')
@cache.memoize(timeout=60 * 20)
def testcache():
    name = 'mink'
    return name + " " + str(cache.get('testcache'))


def ret_ip():
    if request.headers.getlist("X-Forwarded-For"):
        string_ip = request.headers.getlist("X-Forwarded-For")[0]
        t_ip = str(string_ip).split(',')[0]
    else:
        t_ip = request.remote_addr
    #print(t_ip)
    return str(t_ip)
'''

deprecated function for updating main page

'''

def ret_index():
    #r = requests.get("http://127.0.0.1:8080/api/v1/indb/24/Ali.master.cn00/graphite/memory_percent_usedWOBuffersCaches")
    #r = Indb_func.monitor_data(
    #    table='memory_percent_usedWOBuffersCaches', db='graphite', node='Ali.master.cn00')
    #p = Indb_func.monitor_data(
    #    table='cpu_user', db='graphite', node='Ali.master.cn00')
    index_data = {
        #'top': get_toplogy(),
        'user': {
            'name': session['username'],
            'remember_me': session['remember_me'],
            'ip': ret_ip()
        }
       # 'mem': r,
       # 'cpu': p
    }
    current_app.logger.info(index_data)
    return index_data



@frontend.route('/main')
@login_required
#@cache.memoize(timeout=100)
def index():
    s_id = request.args.get('s_id')
    if s_id == None:
        return redirect(url_for('frontend.login'))
    check_id = hashlib.md5(str(session['uid']).encode('utf-8')).hexdigest()
    if s_id == check_id:
        return render_template('index.html', index_data=ret_index())
    else:
        current_app.logger.warning(
            "Session invaild : " + str(s_id) + ' != ' + check_id)
        return redirect(url_for('frontend.logout'))

@frontend.route('/github')
def github_login():
    redirect_uri = url_for('frontend.github_authorized', _external=True)
    print(redirect_uri)
    # More scopes http://developer.github.com/v3/oauth/#scopes
    params = {'redirect_uri': redirect_uri, 'scope': 'user:email'} 
    print(github.get_authorize_url(**params))
    return redirect(github.get_authorize_url(**params))


# same path as on application settings page
@frontend.route('/gcb')
def github_authorized():
    # check to make sure the user authorized the request
    if not 'code' in request.args:
        flash('You did not authorize the request')
        return render_template('info.html'), 200
    # make a request for the access token credentials using code
    redirect_uri = url_for('frontend.github_authorized', _external=True)
    data = dict(code=request.args['code'],
        redirect_uri=redirect_uri,
        scope='user:email,user')
    try:
        auth = github.get_auth_session(data=data)
        session['token'] = auth.access_token
        # the "me" response
        me = auth.get('user').json()
    except Exception as e:
        flash(str(e))
        return render_template('info.html'), 200
    user = User.get_or_create(me)
    login_user(user)
    session['sid'] = hashlib.md5(str(user.id).encode('utf-8')).hexdigest()
    session['username'] = user.name
    return redirect(url_for('frontend.start', s_id=session['sid']))

@frontend.route('/page')
@login_required
def start():
    index_data = {
        'user': {
            'name': session['username'],
            'ip': ret_ip()
        }
    }
    return render_template('index.html', index_data=index_data)

@frontend.route('/')
@frontend.route('/login', methods=['GET', 'POST'])
def login():
    # if g.user is not None and g.user.is_authenticated:
    #    return redirect(url_for('frontend.index'))
    return render_template('info.html'), 200

    form = LoginForm()

    if form.validate_on_submit():

        session['remember_me'] = form.remember_me.data
        #user = User.query.filter_by(name=form.name.data.lower()).first()
        user, auth = User.authenticate(form.name.data, form.password.data)
        if user and auth:
            current_app.logger.info(
                form.name.data + ' checked in with data: ' + str(form.remember_me.data))
            session['username'] = form.name.data
            session['log in'] = True
            session['uid'] = str(user.id)
            session['sid'] = hashlib.md5(
                str(user.id).encode('utf-8')).hexdigest()
            login_user(user, remember=session['remember_me'])
            # current_app.logger.info(str(session))
            return redirect(url_for('frontend.index', s_id=session['sid']))
        else:
            current_app.logger.warning(
                'user ' + form.name.data + ' failed with authentication')
            return render_template('login.html', form=form, failed_auth=True)

    return render_template('login.html', form=form), 200

#@frontend.route('/test/', methods=['POST'])
# def test():
#    data = request.json
#    print(str(data))
#    emit('connect', data, room = '1', namespace='/test')
#    return 'ok',200


@frontend.route('/logout')
def logout():

    logout_user()
    return redirect(url_for('frontend.login'))


@frontend.route('/closed')
@login_required
def closed():

    return render_template('closed.html', index_data=ret_index())
