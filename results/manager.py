# results_manager.py
# Result saving and management system for LDLE experiments

import os
import json
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

class ResultsManager:
    """
    Manages saving and organizing experimental results with timestamps
    """
    
    def __init__(self, base_dir: str = "results"):
        """
        Initialize the results manager
        
        Args:
            base_dir: Base directory for saving results
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.test_dir = self.base_dir / "test"
        self.production_dir = self.base_dir / "production"
        
        self.test_dir.mkdir(exist_ok=True)
        self.production_dir.mkdir(exist_ok=True)
        
        # Current session info
        self.current_session = None
        self.current_run_type = None
        
    def start_session(self, run_type: str = "production", session_name: Optional[str] = None) -> str:
        """
        Start a new experimental session
        
        Args:
            run_type: "test" or "production"
            session_name: Optional custom session name
            
        Returns:
            Session directory path
        """
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        
        if session_name:
            session_id = f"{timestamp}_{session_name}"
        else:
            session_id = timestamp
        
        if run_type == "test":
            session_dir = self.test_dir / session_id
        else:
            session_dir = self.production_dir / session_id
        
        session_dir.mkdir(exist_ok=True)
        
        self.current_session = session_dir
        self.current_run_type = run_type
        
        # Create session metadata
        session_meta = {
            "session_id": session_id,
            "run_type": run_type,
            "start_time": datetime.datetime.now().isoformat(),
            "status": "running"
        }
        
        self.save_json(session_meta, "session_metadata.json")
        
        print(f"📁 Session started: {session_dir}")
        return str(session_dir)
    
    def save_json(self, data: Dict[str, Any], filename: str) -> str:
        """
        Save data as JSON to current session directory
        
        Args:
            data: Data to save
            filename: Filename to save as
            
        Returns:
            Full path to saved file
        """
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        filepath = self.current_session / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved: {filepath}")
        return str(filepath)
    
    def save_text(self, text: str, filename: str) -> str:
        """
        Save text content to current session directory
        
        Args:
            text: Text content to save
            filename: Filename to save as
            
        Returns:
            Full path to saved file
        """
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        filepath = self.current_session / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"💾 Saved: {filepath}")
        return str(filepath)
    
    def save_validation_results(self, results: Dict[str, Any]) -> str:
        """Save Judge validation results"""
        return self.save_json(results, "judge_validation_results.json")
    
    def save_manager_test_results(self, results: Dict[str, Any]) -> str:
        """Save Manager test results"""
        return self.save_json(results, "manager_test_results.json")
    
    def save_pipeline_results(self, 
                            evaluation_results: List[Dict[str, Any]],
                            manager_interactions: List[Dict[str, Any]],
                            summary: Dict[str, Any]) -> Dict[str, str]:
        """
        Save complete pipeline results
        
        Args:
            evaluation_results: Judge evaluation results
            manager_interactions: Manager interaction data
            summary: Summary statistics
            
        Returns:
            Dictionary of saved file paths
        """
        saved_files = {}
        
        # Save individual components
        saved_files['evaluation_results'] = self.save_json(evaluation_results, "evaluation_results.json")
        saved_files['manager_interactions'] = self.save_json(manager_interactions, "manager_interactions.json")
        saved_files['summary'] = self.save_json(summary, "summary.json")
        
        # Save complete results
        complete_results = {
            'summary': summary,
            'detailed_interactions': manager_interactions,
            'judge_evaluations': evaluation_results,
            'metadata': {
                'session_id': self.current_session.name,
                'run_type': self.current_run_type,
                'completion_time': datetime.datetime.now().isoformat()
            }
        }
        
        saved_files['complete_results'] = self.save_json(complete_results, "complete_pipeline_results.json")
        
        # Auto-generate visualizations
        self._generate_visualizations(saved_files['complete_results'])
        
        return saved_files
    
    def end_session(self, final_status: str = "completed") -> str:
        """
        End current session and update metadata
        
        Args:
            final_status: Final session status
            
        Returns:
            Session directory path
        """
        if not self.current_session:
            raise ValueError("No active session to end.")
        
        # Update session metadata
        metadata_file = self.current_session / "session_metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            metadata.update({
                "status": final_status,
                "end_time": datetime.datetime.now().isoformat(),
                "duration": self._calculate_duration(metadata.get("start_time"))
            })
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        session_path = str(self.current_session)
        print(f"✅ Session ended: {session_path}")
        
        # Reset current session
        self.current_session = None
        self.current_run_type = None
        
        return session_path
    
    def _calculate_duration(self, start_time_str: str) -> str:
        """Calculate duration from start time"""
        try:
            start_time = datetime.datetime.fromisoformat(start_time_str)
            duration = datetime.datetime.now() - start_time
            return str(duration)
        except:
            return "unknown"
    
    def list_sessions(self, run_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all saved sessions
        
        Args:
            run_type: Filter by run type ("test" or "production")
            
        Returns:
            List of session information
        """
        sessions = []
        
        directories = []
        if run_type == "test":
            directories = [self.test_dir]
        elif run_type == "production":
            directories = [self.production_dir]
        else:
            directories = [self.test_dir, self.production_dir]
        
        for dir_path in directories:
            if dir_path.exists():
                for session_dir in dir_path.iterdir():
                    if session_dir.is_dir():
                        metadata_file = session_dir / "session_metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            sessions.append({
                                "path": str(session_dir),
                                "metadata": metadata
                            })
        
        return sorted(sessions, key=lambda x: x['metadata'].get('start_time', ''))
    
    def get_session_summary(self, session_path: str) -> Dict[str, Any]:
        """
        Get summary of a specific session
        
        Args:
            session_path: Path to session directory
            
        Returns:
            Session summary information
        """
        session_dir = Path(session_path)
        
        if not session_dir.exists():
            raise ValueError(f"Session directory not found: {session_path}")
        
        summary = {
            "session_path": str(session_dir),
            "files": [],
            "metadata": None
        }
        
        # Get session metadata
        metadata_file = session_dir / "session_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                summary["metadata"] = json.load(f)
        
        # List all files in session
        for file_path in session_dir.iterdir():
            if file_path.is_file():
                summary["files"].append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        return summary
    
    def create_run_summary(self) -> str:
        """Create a summary of all runs"""
        all_sessions = self.list_sessions()
        
        summary = {
            "total_sessions": len(all_sessions),
            "test_sessions": len([s for s in all_sessions if s['metadata']['run_type'] == 'test']),
            "production_sessions": len([s for s in all_sessions if s['metadata']['run_type'] == 'production']),
            "sessions": all_sessions,
            "generated_at": datetime.datetime.now().isoformat()
        }
        
        summary_file = self.base_dir / "all_sessions_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📊 Session summary saved: {summary_file}")
        return str(summary_file)
    
    def _generate_visualizations(self, results_file_path: str) -> None:
        """
        Auto-generate visualizations for experiment results
        
        Args:
            results_file_path: Path to the complete pipeline results JSON file
        """
        try:
            # Import visualization tools
            from english_visualizer import EnglishLDLEVisualizer
            
            # Create visualizations in the same directory as results
            session_dir = Path(results_file_path).parent
            viz_dir = session_dir / "visualizations"
            
            print("🎨 Auto-generating visualizations...")
            
            # Create English visualizations (no Chinese characters)
            visualizer = EnglishLDLEVisualizer(results_file_path, str(viz_dir))
            visualizer.generate_all_visualizations()
            
            print(f"✅ Visualizations saved to: {viz_dir}")
            
        except ImportError as e:
            print(f"⚠️  Could not import visualization tools: {e}")
        except Exception as e:
            print(f"⚠️  Error generating visualizations: {e}")
            print("Continuing without visualizations...")

    def save_conversation_flows(self, conversation_flows: list, session_path: str = None) -> str:
        """Save detailed conversation flows for debugging"""
        if session_path is None:
            session_path = self.session_path
        
        conversations_file = os.path.join(session_path, "conversation_flows.json")
        
        try:
            with open(conversations_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_flows, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"💬 Conversation flows saved: {conversations_file}")
            return conversations_file
            
        except Exception as e:
            print(f"[ERROR] Failed to save conversation flows: {e}")
            return None

# Global results manager instance
_results_manager = ResultsManager()

def get_results_manager() -> ResultsManager:
    """Get the global results manager instance"""
    return _results_manager

def start_test_session(session_name: Optional[str] = None) -> str:
    """Start a test session"""
    return _results_manager.start_session("test", session_name)

def start_production_session(session_name: Optional[str] = None) -> str:
    """Start a production session"""
    return _results_manager.start_session("production", session_name)

def end_session(status: str = "completed") -> str:
    """End current session"""
    return _results_manager.end_session(status) 