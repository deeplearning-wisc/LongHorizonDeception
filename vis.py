#!/usr/bin/env python3
"""
LDLE Visualization Script
Usage: python vis.py <session_name> [options]

Generate comprehensive visualizations for LDLE experiment results.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from visualization.analyzer import ResultsAnalyzer
from visualization.dashboard import create_comprehensive_dashboard, create_quick_overview, list_session_visualizations

def find_session_path(session_name: str, base_path: str = "results/production") -> Optional[str]:
    """
    Find the full path for a session given its name or partial name
    
    Args:
        session_name: Full session name or partial match
        base_path: Base path to search for sessions
        
    Returns:
        Full path to session or None if not found
    """
    
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"❌ Results directory not found: {base_path}")
        return None
    
    # Try exact match first
    exact_path = base_dir / session_name
    if exact_path.exists() and exact_path.is_dir():
        return str(exact_path)
    
    # Try partial match
    matching_sessions = []
    for session_dir in base_dir.iterdir():
        if session_dir.is_dir() and session_name.lower() in session_dir.name.lower():
            matching_sessions.append(session_dir)
    
    if len(matching_sessions) == 1:
        return str(matching_sessions[0])
    elif len(matching_sessions) > 1:
        print(f"❌ Multiple sessions match '{session_name}':")
        for session in matching_sessions:
            print(f"   • {session.name}")
        print("Please specify a more specific session name.")
        return None
    else:
        print(f"❌ No sessions found matching '{session_name}'")
        return None

def list_available_sessions(base_path: str = "results/production") -> None:
    """List all available sessions"""
    
    sessions = ResultsAnalyzer.list_available_sessions(base_path)
    if not sessions:
        print(f"❌ No sessions found in {base_path}")
        return
    
    print(f"📂 Available sessions in {base_path}:")
    for i, session in enumerate(sessions, 1):
        print(f"   {i:2d}. {session}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate visualizations for LDLE experiment results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vis.py session_name                    # Generate full dashboard
  python vis.py session_name --quick            # Generate quick overview only
  python vis.py --list                          # List available sessions
  python vis.py latest                          # Use latest session
  python vis.py 2025_07_07                      # Partial session name match
        """
    )
    
    parser.add_argument(
        'session',
        nargs='?',
        help='Session name or partial name to visualize (use "latest" for most recent)'
    )
    
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Generate quick overview only (faster)'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available sessions'
    )
    
    parser.add_argument(
        '--base-path', '-p',
        default='results/production',
        help='Base path for results (default: results/production)'
    )
    
    parser.add_argument(
        '--show-existing', '-s',
        action='store_true',
        help='Show existing visualizations for the session'
    )
    
    args = parser.parse_args()
    
    # Handle list command
    if args.list:
        list_available_sessions(args.base_path)
        return
    
    # Require session name if not listing
    if not args.session:
        print("❌ Session name required. Use --list to see available sessions.")
        parser.print_help()
        return
    
    # Handle "latest" session
    if args.session.lower() == 'latest':
        session_path = ResultsAnalyzer.find_latest_session(args.base_path)
        if not session_path:
            print(f"❌ No sessions found in {args.base_path}")
            return
        print(f"🔍 Using latest session: {Path(session_path).name}")
    else:
        # Find the specified session
        session_path = find_session_path(args.session, args.base_path)
        if not session_path:
            print("\n💡 Use --list to see available sessions")
            return
    
    # Show existing visualizations if requested
    if args.show_existing:
        existing_viz = list_session_visualizations(session_path)
        if existing_viz:
            print(f"🎨 Existing visualizations in {Path(session_path).name}:")
            for viz_path in existing_viz:
                print(f"   • {Path(viz_path).name}")
        else:
            print(f"📭 No existing visualizations found in {Path(session_path).name}")
        return
    
    print(f"🚀 Starting visualization for session: {Path(session_path).name}")
    print(f"📂 Session path: {session_path}")
    
    try:
        if args.quick:
            # Generate quick overview only
            print("⚡ Generating quick overview...")
            overview_path = create_quick_overview(session_path)
            if overview_path:
                print(f"✅ Quick overview generated: {Path(overview_path).name}")
            else:
                print("❌ Failed to generate quick overview")
        else:
            # Generate comprehensive dashboard
            print("🎨 Generating comprehensive dashboard...")
            generated_plots = create_comprehensive_dashboard(session_path, save_to_session=True)
            
            if generated_plots:
                print(f"\n🎉 Success! Generated {len(generated_plots)} visualizations")
                viz_dir = Path(session_path) / "visualizations"
                print(f"📁 Visualizations saved to: {viz_dir}")
                
                print(f"\n📊 Generated files:")
                for plot_path in generated_plots:
                    file_size = Path(plot_path).stat().st_size / 1024  # KB
                    print(f"   • {Path(plot_path).name} ({file_size:.1f} KB)")
            else:
                print("❌ No visualizations were generated")
                return
    
    except KeyboardInterrupt:
        print("\n⏹️ Visualization cancelled by user")
        return
    except Exception as e:
        print(f"❌ Error during visualization: {e}")
        return
    
    print("\n🎯 Visualization complete!")

if __name__ == "__main__":
    main() 