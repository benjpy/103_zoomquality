import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown

from video_check import check_video_quality
from audio_check import check_audio_quality
from network_check import check_network_quality
from report import analyze_video_results, analyze_audio_results, analyze_network_results

console = Console()

def main():
    console.print(Panel.fit("[bold blue]Video Call Quality Checker[/bold blue]\n[italic]Analyzing your setup for Zoom, Teams, Meet, etc.[/italic]"))
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=False,
    ) as progress:
        
        # Video Check
        task1 = progress.add_task("[cyan]Checking Video Quality...[/cyan]", total=None)
        video_data = check_video_quality(duration=2)
        results['video'] = video_data
        progress.update(task1, completed=100, description="[green]Video Check Complete[/green]")
        
        # Audio Check
        task2 = progress.add_task("[cyan]Checking Audio Quality (Please Speak)...[/cyan]", total=None)
        audio_data = check_audio_quality(duration=3)
        results['audio'] = audio_data
        progress.update(task2, completed=100, description="[green]Audio Check Complete[/green]")
        
        # Network Check
        task3 = progress.add_task("[cyan]Checking Network Speed...[/cyan]", total=None)
        network_data = check_network_quality()
        results['network'] = network_data
        progress.update(task3, completed=100, description="[green]Network Check Complete[/green]")

    # Analyze Results
    video_rating, video_recs = analyze_video_results(results['video'])
    audio_rating, audio_recs = analyze_audio_results(results['audio'])
    network_rating, network_recs = analyze_network_results(results['network'])
    
    # Display Report
    console.print("\n[bold underline]Final Report[/bold underline]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category", style="dim")
    table.add_column("Rating")
    table.add_column("Details")
    
    # Video Row
    v_color = "green" if video_rating == "Excellent" else "yellow" if video_rating == "Good" else "red"
    v_details = f"Brightness: {results['video'].get('avg_brightness', 0):.1f}\nSharpness: {results['video'].get('avg_sharpness', 0):.1f}"
    table.add_row("Video", f"[{v_color}]{video_rating}[/{v_color}]", v_details)
    
    # Audio Row
    a_color = "green" if audio_rating == "Excellent" else "yellow" if audio_rating == "Good" else "red"
    a_details = f"Volume (dB): {results['audio'].get('decibels', -100):.1f}"
    table.add_row("Audio", f"[{a_color}]{audio_rating}[/{a_color}]", a_details)
    
    # Network Row
    n_color = "green" if network_rating == "Excellent" else "yellow" if network_rating == "Good" else "red"
    n_details = f"Down: {results['network'].get('download_mbps', 0):.1f} Mbps\nUp: {results['network'].get('upload_mbps', 0):.1f} Mbps\nPing: {results['network'].get('ping_ms', 0):.0f} ms"
    table.add_row("Network", f"[{n_color}]{network_rating}[/{n_color}]", n_details)
    
    console.print(table)
    
    # Recommendations
    all_recs = video_recs + audio_recs + network_recs
    if all_recs:
        console.print("\n[bold orange1]Recommendations:[/bold orange1]")
        for rec in all_recs:
            console.print(f"- {rec}")
    else:
        console.print("\n[bold green]Everything looks great! You are ready for your call.[/bold green]")

if __name__ == "__main__":
    main()
