from trading_system.execution.live_orders import SupabaseLiveOrderRepository


def test_supabase_live_order_repository_can_be_constructed_without_connection():
    repo = SupabaseLiveOrderRepository("postgresql://example")
    assert repo._database_url == "postgresql://example"
