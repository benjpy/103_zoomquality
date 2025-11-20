import speedtest

def check_network_quality():
    """
    Runs a speedtest to check download, upload, and ping.
    """
    print("Starting network check... This may take a few seconds.")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        
        print("Testing download speed...")
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        
        print("Testing upload speed...")
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        
        ping = st.results.ping
        
        return {
            "download_mbps": download_speed,
            "upload_mbps": upload_speed,
            "ping_ms": ping
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test run
    results = check_network_quality()
    print(results)
