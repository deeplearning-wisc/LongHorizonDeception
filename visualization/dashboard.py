import os
from pathlib import Path
from typing import List, Optional
from .analyzer import ResultsAnalyzer
from .plotter import DeceptionPlotter

def create_comprehensive_dashboard(session_path: str, save_to_session: bool = True) -> List[str]:
    """
    Create comprehensive visualization dashboard for a LDLE session
    
    Args:
        session_path: Path to the session results directory
        save_to_session: Whether to save plots to the session directory
        
    Returns:
        List of paths to generated plots
    """
    
    print(f"🎨 Creating comprehensive dashboard for session: {session_path}")
    
    # Initialize analyzer
    analyzer = ResultsAnalyzer(session_path)
    if not analyzer.load_results():
        print("❌ Failed to load session results")
        return []
    
    # Determine save path
    if save_to_session:
        save_path = Path(session_path) / "visualizations"
    else:
        save_path = Path("./visualizations")
    
    save_path.mkdir(parents=True, exist_ok=True)
    print(f"📁 Saving visualizations to: {save_path}")
    
    # Initialize plotter
    plotter = DeceptionPlotter(save_path)
    
    # Generate all visualizations
    generated_plots = []
    
    try:
        # 1. Intent distribution pie chart
        print("📊 Generating intent distribution...")
        intent_data = analyzer.get_intent_distribution()
        if intent_data:
            plot_path = plotter.plot_intent_distribution(intent_data)
            if plot_path:
                generated_plots.append(plot_path)
        
        # 2. Category distribution pie chart  
        print("📊 Generating category distribution...")
        category_data = analyzer.get_category_distribution()
        if category_data:
            plot_path = plotter.plot_category_distribution(category_data)
            if plot_path:
                generated_plots.append(plot_path)
        
        # 3. Detection comparison bar chart
        print("📊 Generating detection comparison...")
        detection_df = analyzer.get_detection_comparison_data()
        if not detection_df.empty:
            plot_path = plotter.plot_detection_comparison(detection_df)
            if plot_path:
                generated_plots.append(plot_path)
        
        # 4. Trust evolution line chart (legacy)
        print("📊 Generating trust evolution...")
        trust_df = analyzer.get_trust_evolution_data()
        if not trust_df.empty:
            plot_path = plotter.plot_trust_evolution(trust_df)
            if plot_path:
                generated_plots.append(plot_path)
        
        # 4.5. LLM State Dynamics (NEW!)
        print("📊 Generating LLM state dynamics...")
        llm_state_df = analyzer.get_llm_state_evolution_data()
        if not llm_state_df.empty:
            # Generate 2x2 subplot visualization
            plot_path = plotter.plot_llm_state_dynamics(llm_state_df)
            if plot_path:
                generated_plots.append(plot_path)
            
            # Generate unified timeline visualization
            plot_path = plotter.plot_llm_state_timeline(llm_state_df)
            if plot_path:
                generated_plots.append(plot_path)
        
        # 5. Variant-severity combined plot
        print("📊 Generating variant-severity analysis...")
        variant_df = analyzer.get_variant_and_severity_data()
        if not variant_df.empty:
            plot_path = plotter.plot_variant_severity_combined(variant_df)
            if plot_path:
                generated_plots.append(plot_path)
        
        # 6. Summary statistics
        print("📊 Generating summary statistics...")
        stats = analyzer.get_comprehensive_stats()
        if stats:
            plot_path = plotter.create_summary_stats_plot(stats)
            if plot_path:
                generated_plots.append(plot_path)
        
        print(f"✅ Dashboard creation complete!")
        print(f"📈 Generated {len(generated_plots)} visualizations:")
        for plot_path in generated_plots:
            print(f"   • {os.path.basename(plot_path)}")
        
        # Print summary statistics
        if stats:
            print(f"\n📋 Session Summary:")
            print(f"   • Total Tasks: {stats.get('total_tasks', 0)}")
            print(f"   • Deceptive Variants: {stats.get('deceptive_variants_used', 0)}")
            print(f"   • Judge Detection Rate: {stats.get('detection_rate_judge', 0)*100:.1f}%")
            print(f"   • Manager Detection Rate: {stats.get('detection_rate_manager', 0)*100:.1f}%")
            print(f"   • Final Trust Level: {stats.get('final_trust_level', 'UNKNOWN')}")
        
        return generated_plots
        
    except Exception as e:
        print(f"❌ Error creating dashboard: {e}")
        return generated_plots

def create_quick_overview(session_path: str) -> Optional[str]:
    """
    Create a quick overview plot combining key metrics
    
    Args:
        session_path: Path to the session results directory
        
    Returns:
        Path to generated overview plot or None if failed
    """
    
    analyzer = ResultsAnalyzer(session_path)
    if not analyzer.load_results():
        return None
    
    save_path = Path(session_path) / "visualizations"
    save_path.mkdir(parents=True, exist_ok=True)
    
    plotter = DeceptionPlotter(save_path)
    stats = analyzer.get_comprehensive_stats()
    
    if stats:
        return plotter.create_summary_stats_plot(stats)
    
    return None

def list_session_visualizations(session_path: str) -> List[str]:
    """
    List all existing visualizations for a session
    
    Args:
        session_path: Path to the session results directory
        
    Returns:
        List of visualization file paths
    """
    
    viz_path = Path(session_path) / "visualizations"
    if not viz_path.exists():
        return []
    
    viz_files = []
    for file_path in viz_path.glob("*.png"):
        viz_files.append(str(file_path))
    
    return sorted(viz_files) 