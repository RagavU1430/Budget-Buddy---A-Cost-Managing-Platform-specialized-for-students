import calendar
from datetime import date
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db import models
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_assistant_set_budget_and_real_website_update():
    """Verify that asking the assistant to set a budget creates the budget in the DB
    and updates the user's budget limit, preventing the 'Limit ₹0' desync issue.
    """
    uid = uuid.uuid4().hex[:8]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/auth/register/",
            json={
                "username": f"user_{uid}",
                "email": f"user_{uid}@example.com",
                "password": "Password123!",
                "password_confirm": "Password123!",
                "first_name": "Priya",
                "last_name": "Sharma",
                "role": "student",
            },
        )
        assert reg_res.status_code == 201, reg_res.text
        access_token = reg_res.json()["access"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Verify initial budget limit is 0
        bud_res = await client.get("/api/budgets/", headers=auth_headers)
        assert bud_res.status_code == 200
        assert bud_res.json()["count"] == 0

        # Ask assistant to set daily budget: "set a budget of 1000 per day"
        chat_res = await client.post(
            "/api/assistant/chat/",
            headers=auth_headers,
            json={"message": "set a budget of 1000 per day"},
        )
        assert chat_res.status_code == 200, chat_res.text
        chat_data = chat_res.json()
        assert chat_data["action_type"] == "budget_created"
        assert "Monthly Budget Created Successfully" in chat_data["reply"] or "Monthly Budget Updated Successfully" in chat_data["reply"]
        assert "1,000.00 / day" in chat_data["reply"]

        # Verify budget is ACTUALLY in the database now
        bud_after = await client.get("/api/budgets/", headers=auth_headers)
        assert bud_after.status_code == 200
        budgets_list = bud_after.json()["results"]
        assert len(budgets_list) == 1
        
        today = date.today()
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        expected_limit = 1000 * days_in_month
        assert float(budgets_list[0]["limit_amount"]) == float(expected_limit)

        # Test polite variation: "can you set a budget of 500 per day?"
        chat_polite = await client.post(
            "/api/assistant/chat/",
            headers=auth_headers,
            json={"message": "can you set a budget of 500 per day?"},
        )
        assert chat_polite.status_code == 200
        assert chat_polite.json()["action_type"] == "budget_created"


@pytest.mark.asyncio
async def test_assistant_interactive_clarification():
    """Verify that logging spend or income without a category triggers interactive questions."""
    uid = uuid.uuid4().hex[:8]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/auth/register/",
            json={
                "username": f"multi_{uid}",
                "email": f"multi_{uid}@example.com",
                "password": "Password123!",
                "password_confirm": "Password123!",
                "first_name": "Multi",
                "last_name": "Turn",
                "role": "student",
            },
        )
        assert reg_res.status_code == 201
        auth_headers = {"Authorization": f"Bearer {reg_res.json()['access']}"}

        # Step 1: User says "Spent 250" without category
        chat_1 = await client.post(
            "/api/assistant/chat/",
            headers=auth_headers,
            json={"message": "Spent 250"},
        )
        assert chat_1.status_code == 200
        data_1 = chat_1.json()
        assert data_1["action_type"] == "pending_category_clarification"
        assert "Food & Dining" in data_1["reply"]

        # Step 2: User answers "food"
        chat_2 = await client.post(
            "/api/assistant/chat/",
            headers=auth_headers,
            json={"message": "food"},
        )
        assert chat_2.status_code == 200
        data_2 = chat_2.json()
        assert data_2["action_type"] == "expense_created"
        assert "250.00" in data_2["reply"]

        # Verify expense recorded
        exp_res = await client.get("/api/expenses/", headers=auth_headers)
        assert exp_res.status_code == 200
        assert exp_res.json()["count"] == 1
