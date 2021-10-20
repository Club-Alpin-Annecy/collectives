"""" Testing administration """

def test_admin_user(dbauth,client):
    dbauth.login(client)
    response = client.get('/administration/users/add')
    assert response.status_code == 200

