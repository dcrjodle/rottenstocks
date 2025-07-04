#!/usr/bin/env python3
"""
Database Testing Tools Launcher

This script provides a simple menu interface to access all database testing tools.
Perfect for developers who want quick access to testing functionality.

Usage:
    python launcher.py
"""

import os
import sys
import subprocess
import asyncio


class DatabaseTestingLauncher:
    """Simple menu launcher for database testing tools."""
    
    def __init__(self):
        self.tools_dir = os.path.dirname(os.path.abspath(__file__))
        self.backend_dir = os.path.join(self.tools_dir, '..', '..', 'backend')
        
    def print_menu(self):
        """Print the main menu."""
        print("🧪 RottenStocks Database Testing Tools")
        print("=" * 40)
        print()
        print("1. 🔧 Interactive Database Shell")
        print("2. 🌱 Generate Sample Data") 
        print("3. 🔍 Query Builder & Analysis")
        print("4. 🏥 Database Health Check")
        print("5. ⚡ Performance Benchmark")
        print("6. 📊 Quick Database Stats")
        print("7. 🗑️  Clear Database (DANGER)")
        print("8. 📚 Help & Documentation")
        print("9. 🚪 Exit")
        print()
    
    def run_tool(self, script_name: str, args: list = None):
        """Run a tool script with optional arguments."""
        script_path = os.path.join(self.tools_dir, script_name)
        cmd = ['python', script_path]
        if args:
            cmd.extend(args)
        
        try:
            # Change to backend directory to ensure proper imports
            os.chdir(self.backend_dir)
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running {script_name}: {e}")
        except KeyboardInterrupt:
            print("\n⚠️  Operation cancelled by user")
        finally:
            # Change back to tools directory
            os.chdir(self.tools_dir)
    
    def get_user_input(self, prompt: str, default: str = None) -> str:
        """Get user input with optional default."""
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        return input(f"{prompt}: ").strip()
    
    def interactive_shell(self):
        """Launch interactive database shell."""
        print("🔧 Launching Interactive Database Shell...")
        print("Tip: Use 'await db.seed_sample_data()' if you need test data")
        print()
        self.run_tool('interactive_db.py')
    
    def generate_sample_data(self):
        """Launch sample data generator with options."""
        print("🌱 Sample Data Generator")
        print()
        
        stocks = self.get_user_input("Number of stocks", "10")
        experts = self.get_user_input("Number of experts", "5")
        posts = self.get_user_input("Posts per stock", "20")
        
        clear_first = input("Clear existing data first? (y/N): ").strip().lower()
        
        args = [
            '--stocks', stocks,
            '--experts', experts,
            '--posts-per-stock', posts
        ]
        
        if clear_first == 'y':
            args.append('--clear-first')
        
        self.run_tool('generate_samples.py', args)
    
    def query_builder(self):
        """Launch query builder with template selection."""
        print("🔍 Query Builder & Analysis")
        print()
        print("Available templates:")
        print("1. top_rated_stocks - Highest rated stocks")
        print("2. expert_performance - Analyst performance") 
        print("3. sentiment_analysis - Social media sentiment")
        print("4. market_overview - Market statistics")
        print("5. stock_performance - Stock price performance")
        print("6. social_media_trends - Trending on social media")
        print("7. rating_distribution - Rating score distribution")
        print("8. Custom SQL query")
        print()
        
        choice = self.get_user_input("Select template (1-8)")
        
        templates = {
            '1': 'top_rated_stocks',
            '2': 'expert_performance',
            '3': 'sentiment_analysis', 
            '4': 'market_overview',
            '5': 'stock_performance',
            '6': 'social_media_trends',
            '7': 'rating_distribution'
        }
        
        if choice in templates:
            args = ['--template', templates[choice]]
            
            # Ask for export option
            export = input("Export to file? (csv/json/N): ").strip().lower()
            if export in ['csv', 'json']:
                filename = self.get_user_input("Filename", f"results.{export}")
                args.extend(['--export', filename])
            
            self.run_tool('query_builder.py', args)
        elif choice == '8':
            sql = self.get_user_input("Enter SQL query")
            if sql:
                self.run_tool('query_builder.py', ['--sql', sql])
        else:
            print("❌ Invalid choice")
    
    def health_check(self):
        """Launch health check tool."""
        print("🏥 Database Health Check")
        print()
        print("1. Quick check (connection, tables, data counts)")
        print("2. Full comprehensive check")
        print("3. Performance benchmark only")
        print()
        
        choice = self.get_user_input("Select check type (1-3)", "1")
        
        if choice == '1':
            self.run_tool('health_check.py', ['--quick'])
        elif choice == '2':
            self.run_tool('health_check.py', ['--full', '--verbose'])
        elif choice == '3':
            self.run_tool('health_check.py', ['--benchmark'])
        else:
            print("❌ Invalid choice")
    
    def performance_benchmark(self):
        """Run performance benchmarks."""
        print("⚡ Running Performance Benchmarks...")
        self.run_tool('health_check.py', ['--benchmark', '--verbose'])
    
    def quick_stats(self):
        """Show quick database statistics."""
        print("📊 Quick Database Statistics")
        self.run_tool('query_builder.py', ['--template', 'market_overview'])
    
    def clear_database(self):
        """Clear database with confirmation."""
        print("🗑️  DANGER: Clear Database")
        print()
        print("⚠️  This will DELETE ALL DATA in the database!")
        print("This action cannot be undone.")
        print()
        
        confirm1 = input("Type 'DELETE' to confirm: ").strip()
        if confirm1 != 'DELETE':
            print("❌ Operation cancelled")
            return
        
        confirm2 = input("Are you absolutely sure? Type 'YES': ").strip()
        if confirm2 != 'YES':
            print("❌ Operation cancelled")
            return
        
        print("🗑️  Clearing database...")
        self.run_tool('generate_samples.py', ['--clear-first', '--stocks', '0'])
    
    def show_help(self):
        """Show help and documentation."""
        print("📚 Help & Documentation")
        print()
        print("📁 Tool Locations:")
        print(f"   Database tools: {self.tools_dir}")
        print(f"   Backend code: {self.backend_dir}")
        print()
        print("📖 Quick Start:")
        print("   1. Make sure Docker services are running: docker-compose up -d")
        print("   2. Activate Python environment: source backend/venv/bin/activate")
        print("   3. Generate sample data if database is empty")
        print("   4. Use interactive shell for custom testing")
        print()
        print("🔧 Direct Tool Usage:")
        print("   python interactive_db.py          # Interactive shell")
        print("   python generate_samples.py --help # Sample data options")
        print("   python query_builder.py --help    # Query options")
        print("   python health_check.py --help     # Health check options")
        print()
        print("📝 For detailed documentation, see README.md in this directory")
        print()
        input("Press Enter to continue...")
    
    def run(self):
        """Run the main menu loop."""
        while True:
            try:
                os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
                self.print_menu()
                
                choice = input("Select an option (1-9): ").strip()
                print()
                
                if choice == '1':
                    self.interactive_shell()
                elif choice == '2':
                    self.generate_sample_data()
                elif choice == '3':
                    self.query_builder()
                elif choice == '4':
                    self.health_check()
                elif choice == '5':
                    self.performance_benchmark()
                elif choice == '6':
                    self.quick_stats()
                elif choice == '7':
                    self.clear_database()
                elif choice == '8':
                    self.show_help()
                elif choice == '9':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please choose 1-9.")
                
                if choice != '9':
                    input("\nPress Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                input("Press Enter to continue...")


if __name__ == "__main__":
    launcher = DatabaseTestingLauncher()
    launcher.run()