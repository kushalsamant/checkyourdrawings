
class TestAccountEndpoint:
    def test_account_anonymous(self, client: TestClient) -> None:
        response = client.get("/account")
        assert response.status_code == 200
        assert response.json() == {
            "signed_in": False,
            "paid": False,
            "email": None,
        }
