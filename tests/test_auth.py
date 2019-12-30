from collectives.models import User

"""" Testing authentication """

def test_login(client):
    """"Invalide login redirected to login page"""
    response = client.post(
          '/auth/login',
          data={'mail': 'unknown', 'password': 'foobar2'})
    assert response.headers['Location'] == 'http://localhost/auth/login'

    """"Valide login redirected to home page"""
    response = client.post(
          '/auth/login',
          data={'mail': 'admin', 'password': 'foobar2'})
    assert response.headers['Location'] == 'http://localhost/'

def test_loginout(dbauth, client):
    assert dbauth.login(client) == 'http://localhost/'
    #FIXME test userID in session
    assert dbauth.logout() == 'http://localhost/auth/login'

def test_admin_create_valideuser(dbauth,client):
    dbauth.login(client)
    response = client.post('/administration/users/add', data={
                           'mail': 'user1@mail.domain',
                           'password': 'foobar1',
                           'confirm': 'foobar1',
                           'first_name': 'user',
                           'last_name': 'LastName',
                           'license': '987987981234',
                           'phone': '0123456789'})
    assert response.headers['Location'] == 'http://localhost/administration/'
    users = User.query.all()
    #user = User.query.filter_by(mail='user1@mail')
    assert users[1].mail == 'user1@mail.domain'
