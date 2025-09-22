#!/usr/bin/env python3
"""
Command-line interface for Nonprofit Partner Finder
"""

import click
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
import time

from src.collectors.irs_collector import IRS990Collector
from src.collectors.web_scraper import NonprofitWebScraper
from src.collectors.social_media import SocialMediaCollector
from src.core.ranking_engine import NonprofitRankingEngine
from src.analyzers.mission_alignment import MissionAlignmentAnalyzer
from src.analyzers.roi_calculator import PartnershipROICalculator


console = Console()


@click.group()
def cli():
    """Red Cross Nonprofit Partner Finder CLI"""
    pass


@cli.command()
@click.argument('zip_code')
@click.option('--radius', default=25, help='Search radius in miles')
@click.option('--top', default=10, help='Number of top results to show')
@click.option('--min-revenue', default=None, type=float, help='Minimum annual revenue filter')
@click.option('--export', default=None, help='Export results to file (csv or json)')
def search(zip_code, radius, top, min_revenue, export):
    """Search and rank nonprofits in a ZIP code area"""
    
    console.print(f"[bold blue]Searching nonprofits in ZIP {zip_code}...[/bold blue]")
    
    # Initialize collectors
    irs_collector = IRS990Collector()
    ranking_engine = NonprofitRankingEngine()
    
    # Search for nonprofits
    with console.status("[bold green]Searching IRS database..."):
        search_results = irs_collector.search_by_zip(zip_code, radius)
    
    if not search_results:
        console.print("[red]No nonprofits found in this area[/red]")
        return
    
    console.print(f"Found [green]{len(search_results)}[/green] nonprofits")
    
    # Collect detailed data
    nonprofits = []
    for result in track(search_results[:30], description="Collecting nonprofit data..."):
        nonprofit = irs_collector.get_nonprofit_details(result['ein'])
        if nonprofit:
            # Apply revenue filter
            if min_revenue:
                latest = nonprofit.get_latest_financials()
                if latest and latest.total_revenue < min_revenue:
                    continue
            nonprofits.append(nonprofit)
    
    # Rank nonprofits
    console.print("[bold blue]Analyzing and ranking nonprofits...[/bold blue]")
    ranked_nonprofits = ranking_engine.rank_nonprofits(nonprofits)
    
    # Display results
    table = Table(title=f"Top {top} Nonprofit Partners for ZIP {zip_code}")
    table.add_column("Rank", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Mission Align", justify="right")
    table.add_column("ROI Potential", justify="right")
    table.add_column("Revenue", justify="right")
    
    for np in ranked_nonprofits[:top]:
        latest = np.get_latest_financials()
        table.add_row(
            str(np.ranking),
            np.name[:40],
            f"{np.overall_score:.1%}",
            f"{np.mission_alignment.score:.1%}" if np.mission_alignment else "N/A",
            f"${np.partnership_roi.estimated_value:,.0f}" if np.partnership_roi else "N/A",
            f"${latest.total_revenue:,.0f}" if latest else "N/A"
        )
    
    console.print(table)
    
    # Export if requested
    if export:
        export_results(ranked_nonprofits, export, zip_code)
        console.print(f"[green]Results exported to {export}[/green]")


@cli.command()
@click.argument('ein')
@click.option('--deep', is_flag=True, help='Perform deep analysis with web scraping')
def analyze(ein, deep):
    """Analyze a specific nonprofit"""
    
    console.print(f"[bold blue]Analyzing nonprofit EIN: {ein}[/bold blue]")
    
    # Initialize components
    irs_collector = IRS990Collector()
    mission_analyzer = MissionAlignmentAnalyzer()
    roi_calculator = PartnershipROICalculator()
    
    # Get nonprofit data
    with console.status("[bold green]Fetching nonprofit data..."):
        nonprofit = irs_collector.get_nonprofit_details(ein)
    
    if not nonprofit:
        console.print("[red]Nonprofit not found[/red]")
        return
    
    # Basic info panel
    info_text = f"""
[bold]{nonprofit.name}[/bold]
EIN: {nonprofit.ein}
Location: {nonprofit.address.city}, {nonprofit.address.state} {nonprofit.address.zip_code}
Status: {nonprofit.status.value}
Website: {nonprofit.website or 'N/A'}

[italic]{nonprofit.mission_statement[:200]}{'...' if nonprofit.mission_statement and len(nonprofit.mission_statement) > 200 else ''}[/italic]
"""
    console.print(Panel(info_text, title="Nonprofit Information", border_style="blue"))
    
    # Perform analysis
    with console.status("[bold green]Analyzing mission alignment..."):
        mission_alignment = mission_analyzer.analyze_alignment(nonprofit)
    
    with console.status("[bold green]Calculating partnership ROI..."):
        partnership_roi = roi_calculator.calculate_roi(nonprofit)
    
    # Mission alignment panel
    mission_text = f"""
Score: [bold green]{mission_alignment.score:.1%}[/bold green]
Confidence: {mission_alignment.confidence:.1%}

Matched Keywords: {', '.join(mission_alignment.matched_keywords[:5])}

{mission_alignment.explanation}
"""
    console.print(Panel(mission_text, title="Mission Alignment Analysis", border_style="green"))
    
    # ROI panel
    roi_text = f"""
Estimated Value: [bold green]${partnership_roi.estimated_value:,.0f}[/bold green]
Cost Savings: ${partnership_roi.cost_savings:,.0f}
Impact Multiplier: {partnership_roi.impact_multiplier:.1f}x
Reach Expansion: {partnership_roi.reach_expansion:,} new beneficiaries

{partnership_roi.explanation}
"""
    console.print(Panel(roi_text, title="Partnership ROI Analysis", border_style="yellow"))
    
    # Financial summary
    latest = nonprofit.get_latest_financials()
    if latest:
        financial_text = f"""
Year: {latest.year}
Revenue: ${latest.total_revenue:,.0f}
Expenses: ${latest.total_expenses:,.0f}
Assets: ${latest.total_assets:,.0f}
Program Efficiency: {latest.program_expense_ratio:.1%}
Overhead Ratio: {latest.overhead_ratio:.1%}
"""
        console.print(Panel(financial_text, title="Financial Summary", border_style="cyan"))
    
    # Deep analysis if requested
    if deep:
        console.print("\n[bold blue]Performing deep analysis...[/bold blue]")
        web_scraper = NonprofitWebScraper()
        social_collector = SocialMediaCollector()
        
        with console.status("[bold green]Scraping website..."):
            if nonprofit.website:
                web_data = web_scraper.scrape_nonprofit_website(nonprofit)
                console.print(f"[green]✓[/green] Website data collected")
        
        with console.status("[bold green]Analyzing social media..."):
            social_accounts = social_collector.search_social_accounts(nonprofit.name)
            if social_accounts:
                social_data = social_collector.analyze_social_presence(nonprofit.name, social_accounts)
                console.print(f"[green]✓[/green] Social media analyzed: {len(social_data)} platforms")


@cli.command()
@click.argument('ein1')
@click.argument('ein2')
def compare(ein1, ein2):
    """Compare two nonprofits"""
    
    console.print(f"[bold blue]Comparing nonprofits: {ein1} vs {ein2}[/bold blue]")
    
    # Initialize components
    irs_collector = IRS990Collector()
    ranking_engine = NonprofitRankingEngine()
    
    # Get both nonprofits
    with console.status("[bold green]Fetching nonprofit data..."):
        nonprofit1 = irs_collector.get_nonprofit_details(ein1)
        nonprofit2 = irs_collector.get_nonprofit_details(ein2)
    
    if not nonprofit1 or not nonprofit2:
        console.print("[red]One or both nonprofits not found[/red]")
        return
    
    # Analyze both
    ranked = ranking_engine.rank_nonprofits([nonprofit1, nonprofit2])
    
    # Create comparison table
    table = Table(title="Nonprofit Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column(ranked[0].name[:30], justify="right")
    table.add_column(ranked[1].name[:30], justify="right")
    
    # Add comparison rows
    table.add_row("Rank", str(ranked[0].ranking), str(ranked[1].ranking))
    table.add_row("Overall Score", 
                  f"{ranked[0].overall_score:.1%}",
                  f"{ranked[1].overall_score:.1%}")
    
    if ranked[0].mission_alignment and ranked[1].mission_alignment:
        table.add_row("Mission Alignment",
                      f"{ranked[0].mission_alignment.score:.1%}",
                      f"{ranked[1].mission_alignment.score:.1%}")
    
    if ranked[0].partnership_roi and ranked[1].partnership_roi:
        table.add_row("ROI Potential",
                      f"${ranked[0].partnership_roi.estimated_value:,.0f}",
                      f"${ranked[1].partnership_roi.estimated_value:,.0f}")
    
    latest1 = ranked[0].get_latest_financials()
    latest2 = ranked[1].get_latest_financials()
    if latest1 and latest2:
        table.add_row("Annual Revenue",
                      f"${latest1.total_revenue:,.0f}",
                      f"${latest2.total_revenue:,.0f}")
        table.add_row("Program Efficiency",
                      f"{latest1.program_expense_ratio:.1%}",
                      f"{latest2.program_expense_ratio:.1%}")
    
    table.add_row("Programs",
                  str(len(ranked[0].programs)),
                  str(len(ranked[1].programs)))
    
    table.add_row("Stability Score",
                  f"{ranked[0].calculate_stability_score():.1%}",
                  f"{ranked[1].calculate_stability_score():.1%}")
    
    console.print(table)
    
    # Recommendation
    comparison = ranking_engine.compare_nonprofits(ranked[0], ranked[1])
    console.print(f"\n[bold green]Recommendation:[/bold green] {comparison['recommendation']}")


def export_results(nonprofits, filename, zip_code):
    """Export results to file"""
    if filename.endswith('.csv'):
        import csv
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Rank', 'EIN', 'Name', 'Score', 'Mission Alignment', 
                           'ROI Potential', 'Revenue', 'Efficiency'])
            
            for np in nonprofits:
                latest = np.get_latest_financials()
                writer.writerow([
                    np.ranking,
                    np.ein,
                    np.name,
                    f"{np.overall_score:.3f}",
                    f"{np.mission_alignment.score:.3f}" if np.mission_alignment else "",
                    f"{np.partnership_roi.estimated_value:.0f}" if np.partnership_roi else "",
                    f"{latest.total_revenue:.0f}" if latest else "",
                    f"{latest.program_expense_ratio:.3f}" if latest else ""
                ])
    
    else:  # JSON
        data = []
        for np in nonprofits:
            latest = np.get_latest_financials()
            data.append({
                'rank': np.ranking,
                'ein': np.ein,
                'name': np.name,
                'score': np.overall_score,
                'mission_alignment': np.mission_alignment.score if np.mission_alignment else None,
                'roi_potential': np.partnership_roi.estimated_value if np.partnership_roi else None,
                'revenue': latest.total_revenue if latest else None,
                'efficiency': latest.program_expense_ratio if latest else None,
                'website': np.website,
                'mission': np.mission_statement
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)


if __name__ == '__main__':
    cli()