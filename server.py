from mcp.server.fastmcp import FastMCP
from live3 import (
    load_state,
    read_new_logs,
    extract_latest_imei_locations,
    chat_with_model
)

mcp = FastMCP("gps-agent")


@mcp.tool()
def refresh_logs() -> str:
    logs = read_new_logs()

    if logs.strip():
        extract_latest_imei_locations(logs)
        return "GPS logs refreshed"

    return "No new logs"


@mcp.tool()
def get_all_vehicles() -> str:
    state = load_state()

    if not state:
        return "No vehicles found"

    output = []

    for imei, data in state.items():
        output.append(
            f"""
IMEI: {imei}
Time: {data['timestamp']}
Direction: {data['direction']}
Speed: {data['speed']}
Lat: {data['lat']}
Lon: {data['lon']}
"""
        )

    return "\n".join(output)


@mcp.tool()
def analyze_fleet() -> str:
    state = load_state()

    prompt = f"""
    Analyze GPS fleet data.
    Detect:
    - suspicious movement
    - high speed
    - inactive vehicles
    - anomalies

    Data:
    {state}
    """

    return chat_with_model(prompt)


if __name__ == "__main__":
    mcp.run()