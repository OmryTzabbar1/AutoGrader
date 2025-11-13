"""
Rich terminal output formatting for CLI.

Provides colorized output, progress bars, and formatted tables for CLI commands.
"""

import sys
from typing import Optional, Dict, Any, List
from pathlib import Path


class TerminalOutput:
    """
    Handles formatted terminal output with colors and progress indicators.

    Uses ANSI color codes for colorization. Falls back to plain text
    if terminal doesn't support colors.
    """

    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'gray': '\033[90m'
    }

    def __init__(self, use_colors: bool = True):
        """
        Initialize terminal output formatter.

        Args:
            use_colors: Whether to use ANSI color codes
        """
        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """Check if terminal supports color output."""
        # Windows CMD and PowerShell support ANSI colors in Windows 10+
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    def color(self, text: str, color: str) -> str:
        """
        Apply color to text.

        Args:
            text: Text to colorize
            color: Color name from COLORS dict

        Returns:
            Colorized text (or plain text if colors disabled)
        """
        if not self.use_colors:
            return text

        color_code = self.COLORS.get(color, '')
        reset = self.COLORS['reset']
        return f"{color_code}{text}{reset}"

    def success(self, message: str) -> None:
        """Print success message in green."""
        print(self.color(f"✓ {message}", 'green'))

    def error(self, message: str) -> None:
        """Print error message in red."""
        print(self.color(f"✗ {message}", 'red'), file=sys.stderr)

    def warning(self, message: str) -> None:
        """Print warning message in yellow."""
        print(self.color(f"⚠ {message}", 'yellow'))

    def info(self, message: str) -> None:
        """Print info message in blue."""
        print(self.color(f"ℹ {message}", 'blue'))

    def header(self, message: str) -> None:
        """Print header message in bold."""
        print(self.color(f"\n{message}", 'bold'))

    def section(self, title: str) -> None:
        """Print section divider."""
        width = 60
        print(self.color(f"\n{'─' * width}", 'gray'))
        print(self.color(f"{title}", 'cyan'))
        print(self.color(f"{'─' * width}", 'gray'))

    def progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """
        Generate a text-based progress bar.

        Args:
            current: Current progress value
            total: Total progress value
            width: Width of progress bar in characters

        Returns:
            Formatted progress bar string
        """
        if total == 0:
            percent = 0
        else:
            percent = (current / total) * 100

        filled = int((current / total) * width) if total > 0 else 0
        bar = '█' * filled + '░' * (width - filled)

        progress_text = f"[{bar}] {percent:.1f}% ({current}/{total})"

        if percent < 50:
            return self.color(progress_text, 'red')
        elif percent < 80:
            return self.color(progress_text, 'yellow')
        else:
            return self.color(progress_text, 'green')

    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        """
        Print formatted table.

        Args:
            headers: Column headers
            rows: Table rows
        """
        if not rows:
            return

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print header
        header_row = " | ".join(
            h.ljust(col_widths[i]) for i, h in enumerate(headers)
        )
        print(self.color(header_row, 'bold'))
        print(self.color("─" * len(header_row), 'gray'))

        # Print rows
        for row in rows:
            row_text = " | ".join(
                str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
            )
            print(row_text)

    def grading_summary(self, result: Dict[str, Any]) -> None:
        """
        Print formatted grading result summary.

        Args:
            result: Grading result dictionary
        """
        self.section("Grading Summary")

        # Basic info
        print(f"Submission ID:  {self.color(result['submission_id'], 'cyan')}")
        print(f"Self-Grade:     {result['self_grade']}")

        # Final score with color based on grade
        final_score = result['final_score']
        if final_score >= 90:
            score_color = 'green'
        elif final_score >= 80:
            score_color = 'cyan'
        elif final_score >= 70:
            score_color = 'yellow'
        else:
            score_color = 'red'

        print(f"Final Score:    {self.color(f'{final_score:.2f}', score_color)}")
        print(f"Difference:     {final_score - result['self_grade']:.2f}")
        print(f"Processing:     {result['processing_time_seconds']:.2f}s")

        # Comparison message
        if 'comparison_message' in result:
            print(f"\n{result['comparison_message']}")

    def category_breakdown(self, breakdown: Dict[str, Dict[str, Any]]) -> None:
        """
        Print category-level score breakdown.

        Args:
            breakdown: Category breakdown dictionary
        """
        self.section("Category Breakdown")

        headers = ["Category", "Weight", "Score"]
        rows = []

        for category_name, data in sorted(breakdown.items()):
            weight = f"{data['total_weight']:.2f}"
            score = f"{data['weighted_score']:.2f}"
            rows.append([category_name, weight, score])

        self.table(headers, rows)

    def criterion_details(self, evaluations: List[Dict[str, Any]]) -> None:
        """
        Print detailed criterion evaluations.

        Args:
            evaluations: List of criterion evaluation dictionaries
        """
        self.section("Criterion Details")

        for eval_data in sorted(evaluations, key=lambda x: x['score'], reverse=True):
            criterion_name = eval_data['criterion_name']
            score = eval_data['score']
            severity = eval_data['severity']

            # Color based on score
            if score >= 90:
                score_color = 'green'
            elif score >= 70:
                score_color = 'cyan'
            else:
                score_color = 'yellow'

            print(f"\n{self.color(criterion_name, 'bold')}: "
                  f"{self.color(f'{score:.1f}', score_color)} "
                  f"({severity})")

            if eval_data.get('strengths'):
                print(self.color("  Strengths:", 'green'))
                for strength in eval_data['strengths'][:2]:  # Show top 2
                    print(f"    • {strength}")

            if eval_data.get('weaknesses'):
                print(self.color("  Weaknesses:", 'red'))
                for weakness in eval_data['weaknesses'][:2]:  # Show top 2
                    print(f"    • {weakness}")

    def cost_summary(self, cost_data: Dict[str, Any]) -> None:
        """
        Print API cost summary.

        Args:
            cost_data: Cost tracking data
        """
        self.section("Cost Summary")

        total_cost = cost_data.get('total_cost', 0.0)
        api_calls = cost_data.get('api_calls', 0)
        total_tokens = cost_data.get('total_tokens', 0)

        print(f"Total Cost:     ${self.color(f'{total_cost:.4f}', 'yellow')}")
        print(f"API Calls:      {api_calls}")
        print(f"Total Tokens:   {total_tokens:,}")

        if api_calls > 0:
            avg_cost = total_cost / api_calls
            print(f"Avg Cost/Call:  ${avg_cost:.4f}")

    def file_paths(self, paths: Dict[str, str]) -> None:
        """
        Print generated file paths.

        Args:
            paths: Dictionary of format -> file path
        """
        self.section("Generated Files")

        for format_name, file_path in paths.items():
            print(f"{format_name.upper():12} → {self.color(file_path, 'cyan')}")


# Global instance
output = TerminalOutput()
