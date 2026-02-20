#!/usr/bin/env python3
"""
Security scanner example using safe-file-walker.
Simulates malware scanning, suspicious file detection, and audit logging.
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime
from safe_file_walker import SafeFileWalker, SafeWalkConfig


class SecurityScanner:
    """Example security scanner using safe-file-walker."""
    
    def __init__(self, root_path):
        self.root_path = Path(root_path).resolve()
        self.findings = []
        self.scan_stats = {
            'files_scanned': 0,
            'suspicious_files': 0,
            'large_files': 0,
            'executables': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _is_suspicious_filename(self, filename):
        """Check for suspicious file patterns."""
        suspicious_patterns = [
            'malware', 'virus', 'trojan', 'ransomware',
            '.exe', '.bat', '.cmd', '.ps1', '.sh',
            'password', 'secret', 'confidential'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in suspicious_patterns)
    
    def _is_executable(self, filepath):
        """Check if file is executable (simplified)."""
        return filepath.suffix.lower() in {'.exe', '.bat', '.cmd', '.sh', '.py'}
    
    def _calculate_file_hash(self, filepath):
        """Calculate SHA256 hash of file (for known malware detection)."""
        try:
            hasher = hashlib.sha256()
            with open(filepath, 'rb') as f:
                # Read first 64KB for quick hash
                chunk = f.read(65536)
                hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, IOError):
            return None
    
    def scan_file(self, filepath):
        """Analyze a single file for security issues."""
        self.scan_stats['files_scanned'] += 1
        
        try:
            stat = filepath.stat()
            findings = []
            
            # Check file size
            if stat.st_size > 100 * 1024 * 1024:  # > 100MB
                findings.append('large_file')
                self.scan_stats['large_files'] += 1
            
            # Check filename
            if self._is_suspicious_filename(filepath.name):
                findings.append('suspicious_name')
                self.scan_stats['suspicious_files'] += 1
            
            # Check if executable
            if self._is_executable(filepath):
                findings.append('executable')
                self.scan_stats['executables'] += 1
            
            # Calculate hash (could compare against malware DB)
            file_hash = self._calculate_file_hash(filepath)
            
            if findings:
                self.findings.append({
                    'path': str(filepath),
                    'findings': findings,
                    'size': stat.st_size,
                    'hash': file_hash,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
                
        except (OSError, IOError) as e:
            # Log permission errors, etc.
            pass
    
    def run_scan(self):
        """Run security scan using safe-file-walker."""
        print(f"Starting security scan of: {self.root_path}")
        print("=" * 60)
        
        self.scan_stats['start_time'] = datetime.now()
        
        # Configure walker with security-appropriate settings
        config = SafeWalkConfig(
            root=self.root_path,
            follow_symlinks=False,        # Never follow symlinks (security!)
            max_depth=10,                 # Limit recursion depth
            max_rate_mb_per_sec=5.0,      # Don't overload I/O
            timeout_sec=300,              # 5 minute timeout
            deterministic=True,           # Reproducible order
            max_unique_files=100000       # Reasonable cache size
        )
        
        # Run the scan
        with SafeFileWalker(config) as walker:
            file_count = 0
            for filepath in walker:
                self.scan_file(filepath)
                file_count += 1
                
                # Progress indicator
                if file_count % 100 == 0:
                    print(f"  Scanned {file_count} files...")
            
            # Get walker statistics
            walker_stats = walker.stats
        
        self.scan_stats['end_time'] = datetime.now()
        
        # Print results
        self._print_report(walker_stats)
        
        # Save findings to file
        self._save_findings()
    
    def _print_report(self, walker_stats):
        """Print scan report."""
        print("\n" + "=" * 60)
        print("SECURITY SCAN REPORT")
        print("=" * 60)
        
        duration = (self.scan_stats['end_time'] - 
                   self.scan_stats['start_time']).total_seconds()
        
        print(f"\nScan Statistics:")
        print(f"  Files scanned:     {self.scan_stats['files_scanned']:,}")
        print(f"  Scan duration:     {duration:.1f} seconds")
        print(f"  Files/second:      {self.scan_stats['files_scanned'] / max(duration, 0.1):.1f}")
        
        print(f"\nWalker Statistics:")
        print(f"  Files yielded:     {walker_stats.files_yielded:,}")
        print(f"  Files skipped:     {walker_stats.files_skipped:,}")
        print(f"  Dirs skipped:      {walker_stats.dirs_skipped:,}")
        print(f"  Bytes processed:   {walker_stats.bytes_processed / 1024 / 1024:.1f} MB")
        
        print(f"\nSecurity Findings:")
        print(f"  Suspicious files:  {self.scan_stats['suspicious_files']}")
        print(f"  Large files (>100MB): {self.scan_stats['large_files']}")
        print(f"  Executables:       {self.scan_stats['executables']}")
        print(f"  Total findings:    {len(self.findings)}")
        
        if self.findings:
            print(f"\nTop findings:")
            for i, finding in enumerate(self.findings[:5], 1):
                print(f"  {i}. {finding['path']}")
                print(f"     Findings: {', '.join(finding['findings'])}")
                print(f"     Size: {finding['size'] / 1024:.1f} KB")
        
        print(f"\nScan completed at: {self.scan_stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def _save_findings(self):
        """Save findings to JSON file."""
        if not self.findings:
            return
        
        report = {
            'scan_info': {
                'root_path': str(self.root_path),
                'start_time': self.scan_stats['start_time'].isoformat(),
                'end_time': self.scan_stats['end_time'].isoformat(),
                'duration_seconds': (self.scan_stats['end_time'] - 
                                   self.scan_stats['start_time']).total_seconds()
            },
            'statistics': self.scan_stats,
            'findings': self.findings
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"security_scan_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")


def example_basic_scan():
    """Run a basic security scan."""
    print("=== Basic Security Scan ===")
    
    # Scan current directory (adjust path as needed)
    scanner = SecurityScanner(".")
    scanner.run_scan()


def example_with_custom_rules():
    """Example with custom security rules."""
    print("\n=== Custom Security Rules ===")
    
    class CustomScanner(SecurityScanner):
        def _is_suspicious_filename(self, filename):
            # Add custom rules
            custom_patterns = [
                'backup', 'archive', 'temp',
                '.log', '.tmp', '.cache'
            ]
            filename_lower = filename.lower()
            
            # Check for suspicious patterns
            if super()._is_suspicious_filename(filename):
                return True
            
            # Check for custom patterns
            return any(pattern in filename_lower for pattern in custom_patterns)
    
    scanner = CustomScanner(".")
    scanner.run_scan()


if __name__ == "__main__":
    example_basic_scan()
    # example_with_custom_rules()  # Uncomment to try custom scanner