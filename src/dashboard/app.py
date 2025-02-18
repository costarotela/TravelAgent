"""Dashboard for monitoring travel providers."""

import time
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Travel Provider Monitor", page_icon="✈️", layout="wide")

# Estilos
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
    }
    .success { color: #28a745; }
    .warning { color: #ffc107; }
    .danger { color: #dc3545; }
    </style>
""",
    unsafe_allow_html=True,
)


def get_provider_status():
    """Get provider status from API."""
    try:
        response = requests.get("http://localhost:8001/monitoring/status")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error getting provider status: {str(e)}")
        return None


def create_metrics_chart(metrics_data, metric_name):
    """Create a line chart for a specific metric."""
    if not metrics_data:
        return None

    df = pd.DataFrame(metrics_data)
    fig = px.line(
        df,
        x="timestamp",
        y=metric_name,
        title=f"{metric_name.replace('_', ' ').title()} over time",
    )
    return fig


def main():
    """Main dashboard application."""
    st.title("✈️ Travel Provider Monitor")

    # Actualización automática
    auto_refresh = st.sidebar.checkbox("Auto refresh", value=True)
    refresh_interval = st.sidebar.slider(
        "Refresh interval (seconds)", min_value=5, max_value=60, value=10
    )

    # Contenedor principal
    main_container = st.container()

    while True:
        with main_container:
            status_data = get_provider_status()

            if status_data:
                # Estado general
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Provider Status",
                        status_data["status"].upper(),
                        delta=None,
                        delta_color="normal",
                    )

                with col2:
                    st.metric(
                        "Last Check",
                        datetime.fromisoformat(status_data["last_check"]).strftime(
                            "%H:%M:%S"
                        ),
                        delta=None,
                    )

                with col3:
                    total_ops = sum(
                        m["total_calls"] for m in status_data["metrics"].values()
                    )
                    st.metric("Total Operations", total_ops)

                # Métricas detalladas
                st.subheader("Operation Metrics")
                for op_name, metrics in status_data["metrics"].items():
                    with st.expander(f"{op_name.replace('_', ' ').title()} Details"):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            success_rate = metrics["success_rate"] * 100
                            st.metric(
                                "Success Rate",
                                f"{success_rate:.1f}%",
                                delta=None,
                                delta_color="normal",
                            )

                        with col2:
                            st.metric(
                                "Average Latency",
                                f"{metrics['average_latency']:.2f}s",
                                delta=None,
                            )

                        with col3:
                            cache_rate = metrics["cache_hit_rate"] * 100
                            st.metric(
                                "Cache Hit Rate", f"{cache_rate:.1f}%", delta=None
                            )

                        with col4:
                            st.metric("Total Calls", metrics["total_calls"], delta=None)

                        # Errores recientes
                        if metrics["recent_errors"]:
                            st.warning(
                                "Recent Errors: " + ", ".join(metrics["recent_errors"])
                            )

                        # Último error
                        if metrics["last_error"]:
                            st.error(
                                f"Last Error ({metrics['last_error']}): "
                                + f"{metrics['last_error_message']}"
                            )

                # Gráficos
                st.subheader("Performance Graphs")
                col1, col2 = st.columns(2)

                with col1:
                    latency_data = [
                        {
                            "operation": op,
                            "latency": m["average_latency"],
                            "calls": m["total_calls"],
                        }
                        for op, m in status_data["metrics"].items()
                    ]
                    if latency_data:
                        df = pd.DataFrame(latency_data)
                        fig = px.bar(
                            df,
                            x="operation",
                            y="latency",
                            title="Average Latency by Operation",
                            color="calls",
                            labels={
                                "operation": "Operation",
                                "latency": "Average Latency (s)",
                                "calls": "Total Calls",
                            },
                        )
                        st.plotly_chart(fig, use_container_width=True)

                with col2:
                    success_data = [
                        {
                            "operation": op,
                            "success_rate": m["success_rate"] * 100,
                            "cache_rate": m["cache_hit_rate"] * 100,
                        }
                        for op, m in status_data["metrics"].items()
                    ]
                    if success_data:
                        df = pd.DataFrame(success_data)
                        fig = go.Figure()
                        fig.add_trace(
                            go.Bar(
                                name="Success Rate",
                                x=df["operation"],
                                y=df["success_rate"],
                                marker_color="green",
                            )
                        )
                        fig.add_trace(
                            go.Bar(
                                name="Cache Hit Rate",
                                x=df["operation"],
                                y=df["cache_rate"],
                                marker_color="blue",
                            )
                        )
                        fig.update_layout(
                            title="Success and Cache Hit Rates",
                            barmode="group",
                            yaxis_title="Percentage (%)",
                        )
                        st.plotly_chart(fig, use_container_width=True)

            if not auto_refresh:
                break

            time.sleep(refresh_interval)
            main_container.empty()


if __name__ == "__main__":
    main()
