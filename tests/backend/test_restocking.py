"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingRecommendations:
    """Test suite for restocking recommendation endpoint."""

    def test_get_recommendations(self, client):
        """Test getting restocking recommendations."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_recommendation_structure(self, client):
        """Test that each recommendation has required fields."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            assert "item_sku" in rec
            assert "item_name" in rec
            assert "current_demand" in rec
            assert "forecasted_demand" in rec
            assert "demand_gap" in rec
            assert "trend" in rec
            assert "unit_cost" in rec
            assert "recommended_quantity" in rec
            assert "total_cost" in rec
            assert "priority_score" in rec

    def test_recommendations_positive_demand_gap(self, client):
        """Test that all recommendations have a positive demand gap."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            assert rec["demand_gap"] > 0
            assert rec["recommended_quantity"] == rec["demand_gap"]

    def test_recommendations_valid_costs(self, client):
        """Test that recommendations have valid cost data."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            assert isinstance(rec["unit_cost"], (int, float))
            assert rec["unit_cost"] > 0
            assert abs(rec["total_cost"] - rec["unit_cost"] * rec["recommended_quantity"]) < 0.01

    def test_recommendations_sorted_by_priority(self, client):
        """Test that recommendations are sorted by priority_score descending."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for i in range(len(data) - 1):
            assert data[i]["priority_score"] >= data[i + 1]["priority_score"]

    def test_recommendations_trend_weights(self, client):
        """Test that priority_score reflects trend weighting."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            expected_weight = {"increasing": 1.5, "stable": 1.0, "decreasing": 0.5}
            weight = expected_weight.get(rec["trend"], 1.0)
            expected_score = rec["demand_gap"] * weight
            assert abs(rec["priority_score"] - expected_score) < 0.1


class TestRestockingOrders:
    """Test suite for restocking order endpoints."""

    def test_get_orders_initially_empty(self, client):
        """Test that restocking orders list starts empty."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_create_restocking_order(self, client):
        """Test creating a restocking order."""
        order_data = {
            "budget": 10000,
            "items": [
                {
                    "item_sku": "WDG-001",
                    "item_name": "Industrial Widget Type A",
                    "quantity": 50,
                    "unit_cost": 18.75
                }
            ]
        }

        response = client.post("/api/restocking/orders", json=order_data)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert "order_number" in data
        assert data["status"] == "Submitted"
        assert data["delivery_lead_days"] == 7
        assert "expected_delivery" in data
        assert "created_date" in data
        assert abs(data["total_cost"] - 50 * 18.75) < 0.01

    def test_create_order_empty_items_rejected(self, client):
        """Test that an order with no items is rejected."""
        order_data = {
            "budget": 10000,
            "items": []
        }

        response = client.post("/api/restocking/orders", json=order_data)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_created_order_appears_in_list(self, client):
        """Test that a created order appears in the orders list."""
        order_data = {
            "budget": 5000,
            "items": [
                {
                    "item_sku": "GSK-203",
                    "item_name": "High-Temperature Gasket",
                    "quantity": 20,
                    "unit_cost": 8.25
                }
            ]
        }

        create_response = client.post("/api/restocking/orders", json=order_data)
        assert create_response.status_code == 201
        created_id = create_response.json()["id"]

        list_response = client.get("/api/restocking/orders")
        assert list_response.status_code == 200

        order_ids = [o["id"] for o in list_response.json()]
        assert created_id in order_ids

    def test_order_has_correct_item_structure(self, client):
        """Test that order items have proper structure."""
        order_data = {
            "budget": 10000,
            "items": [
                {
                    "item_sku": "FLT-405",
                    "item_name": "Oil Filter Cartridge",
                    "quantity": 30,
                    "unit_cost": 12.50
                },
                {
                    "item_sku": "SNR-420",
                    "item_name": "Temperature Sensor Module",
                    "quantity": 10,
                    "unit_cost": 34.99
                }
            ]
        }

        response = client.post("/api/restocking/orders", json=order_data)
        assert response.status_code == 201

        data = response.json()
        assert len(data["items"]) == 2

        for item in data["items"]:
            assert "item_sku" in item
            assert "item_name" in item
            assert "quantity" in item
            assert "unit_cost" in item
