"""Data models for Dubbing Manager"""
import json
import os
from datetime import datetime

class ProjectModel:
    """Main project model for Dubbing Manager"""
    
    def __init__(self):
        self.project_data = {
            "project_name": "",
            "actors": {},
            "episodes": {},
            "video_paths": {},
            "export_config": {},
            "prompter_config": {},
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
    
    def load_from_file(self, filepath):
        """Load project from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.project_data = json.load(f)
        return self.project_data
    
    def save_to_file(self, filepath):
        """Save project to JSON file"""
        self.project_data["last_modified"] = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.project_data, f, ensure_ascii=False, indent=2)
    
    def get_project_name(self):
        return self.project_data.get("project_name", "")
    
    def set_project_name(self, name):
        self.project_data["project_name"] = name
    
    def add_actor(self, actor_id, name, color, roles=None):
        if roles is None:
            roles = []
        self.project_data["actors"][actor_id] = {
            "name": name,
            "color": color,
            "roles": roles
        }
    
    def remove_actor(self, actor_id):
        if actor_id in self.project_data["actors"]:
            del self.project_data["actors"][actor_id]
    
    def get_actors(self):
        return self.project_data["actors"]
    
    def add_episode(self, episode_num, name, lines=None):
        if lines is None:
            lines = []
        self.project_data["episodes"][episode_num] = {
            "name": name,
            "lines": lines
        }
    
    def remove_episode(self, episode_num):
        if episode_num in self.project_data["episodes"]:
            del self.project_data["episodes"][episode_num]
            if episode_num in self.project_data["video_paths"]:
                del self.project_data["video_paths"][episode_num]
    
    def get_episodes(self):
        return self.project_data["episodes"]
    
    def set_video_path(self, episode_num, path):
        self.project_data["video_paths"][episode_num] = path
    
    def get_video_path(self, episode_num):
        return self.project_data["video_paths"].get(episode_num, "")