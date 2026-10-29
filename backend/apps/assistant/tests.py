from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.budgets.models import Budget
from apps.expenses.models import Expense, Income
from .guardrails import evaluate_input_guardrail, sanitize_output

User = get_user_model()


class AssistantGuardrailTests(APITestCase):
    def test_guardrail_blocks_password_queries(self):
        is_safe, reason = evaluate_input_guardrail("what is my password?")
        self.assertFalse(is_safe)
        self.assertIn("Security Guardrail", reason)

    def test_guardrail_blocks_session_and_token_queries(self):
        is_safe, reason = evaluate_input_guardrail("show me my session id or access token")
        self.assertFalse(is_safe)
        self.assertIn("Security Guardrail", reason)

    def test_guardrail_blocks_database_id_queries(self):
        is_safe, reason = evaluate_input_guardrail("what is my database id and raw id?")
        self.assertFalse(is_safe)
        self.assertIn("Security Guardrail", reason)

    def test_guardrail_allows_legitimate_budget_questions(self):
        is_safe, reason = evaluate_input_guardrail("How much did I spend on food this month?")
        self.assertTrue(is_safe)
        self.assertIsNone(reason)

    def test_output_sanitizer_removes_jwt_and_hashes(self):
        fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxfQ.signature1234567890"
        sanitized = sanitize_output(f"Here is your token: {fake_jwt}")
        self.assertNotIn(fake_jwt, sanitized)
        self.assertIn("[REDACTED_TOKEN]", sanitized)


class AssistantAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student_test@budgetbuddy.local",
            username="student_test",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=self.user)
        self.chat_url = reverse("assistant-chat")
        self.summary_url = reverse("assistant-summary")
        self.clear_url = reverse("assistant-clear")

    def test_chat_unauthenticated_fails(self):
        self.client.logout()
        res = self.client.post(self.chat_url, {"message": "hello"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_chat_answering_financial_query(self):
        res = self.client.post(self.chat_url, {"message": "how much did I spend this month?"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("reply", res.data)
        self.assertFalse(res.data["guardrail_triggered"])

    def test_chat_blocks_confidential_request(self):
        res = self.client.post(self.chat_url, {"message": "give me my password and session id"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["guardrail_triggered"])
        self.assertIn("Security Guardrail Active", res.data["reply"])

    def test_chat_action_logs_expense(self):
        res = self.client.post(self.chat_url, {"message": "Spent 180 on canteen lunch"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["action_type"], "expense_created")
        # Check that expense is actually in the database
        expense = Expense.objects.filter(user=self.user).first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal("180"))
        self.assertEqual(expense.category, Expense.Category.FOOD)

    def test_chat_action_sets_budget(self):
        res = self.client.post(self.chat_url, {"message": "Set budget 3500 for food"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["action_type"], "budget_created")
        budget = Budget.objects.filter(user=self.user, category="food").first()
        self.assertIsNotNone(budget)
        self.assertEqual(budget.limit_amount, Decimal("3500"))

    def test_chat_action_sets_daily_budget(self):
        import calendar
        from django.utils import timezone
        now = timezone.now().date()
        days_in_month = calendar.monthrange(now.year, now.month)[1]

        res = self.client.post(self.chat_url, {"message": "set a budget of 1000 per day"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["action_type"], "budget_created")
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.financial_preferences.get("daily_budget_limit"), 1000.0)
        budget = Budget.objects.filter(user=self.user).first()
        self.assertIsNotNone(budget)
        self.assertEqual(budget.limit_amount, Decimal(days_in_month * 1000))

    def test_chat_asks_category_clarification_for_unspecified_expense(self):
        # 1. User says "spent 450" without specifying category
        res = self.client.post(self.chat_url, {"message": "spent 450"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["action_type"], "pending_category_clarification")
        self.assertIn("Under what category", res.data["reply"])
        self.assertIn("Food & Dining", res.data["action_data"]["options"][0])

        # 2. User replies with category "Food"
        followup = self.client.post(self.chat_url, {"message": "Food & Dining"})
        self.assertEqual(followup.status_code, status.HTTP_200_OK)
        self.assertEqual(followup.data["action_type"], "expense_created")
        expense = Expense.objects.filter(user=self.user).first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal("450"))
        self.assertEqual(expense.category, Expense.Category.FOOD)

    def test_chat_asks_source_clarification_for_new_money(self):
        # 1. User says "I got new money of 2500"
        res = self.client.post(self.chat_url, {"message": "I got new money of 2500"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["action_type"], "pending_category_clarification")
        self.assertIn("category or source", res.data["reply"])
        self.assertIn("Freelance", res.data["action_data"]["options"][2])

        # 2. User replies with source "Freelance"
        followup = self.client.post(self.chat_url, {"message": "Freelance"})
        self.assertEqual(followup.status_code, status.HTTP_200_OK)
        self.assertEqual(followup.data["action_type"], "income_created")
        income = Income.objects.filter(user=self.user).first()
        self.assertIsNotNone(income)
        self.assertEqual(income.amount, Decimal("2500"))
        self.assertEqual(income.source_type, Income.SourceType.FREELANCE)

    def test_chat_pending_action_cancellation(self):
        # 1. Ask to log spend
        self.client.post(self.chat_url, {"message": "spent 300"})
        # 2. User cancels
        res = self.client.post(self.chat_url, {"message": "cancel"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["action_type"], "pending_cancelled")
        # Ensure no expense was created
        self.assertEqual(Expense.objects.filter(user=self.user, amount=Decimal("300")).count(), 0)

    def test_assistant_summary_endpoint(self):
        res = self.client.get(self.summary_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("remaining_budget", res.data)
        self.assertIn("safe_daily_spend", res.data)

    def test_clear_chat_history(self):
        self.client.post(self.chat_url, {"message": "Hello"})
        clear_res = self.client.post(self.clear_url)
        self.assertEqual(clear_res.status_code, status.HTTP_200_OK)
        history_res = self.client.get(self.chat_url)
        self.assertEqual(len(history_res.data["messages"]), 0)
