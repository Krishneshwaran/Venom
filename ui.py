"""Simple Tkinter UI to view and manage reports.

Provides:
- List available weekly PDF reports
- Regenerate the latest report (calls aggregator.save_weekly_report_pdf)
- Copy selected report to Downloads (calls download_report.copy_to_downloads)

The UI is optional; it launches when run directly.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import sys

from logger import ActivityLogger
from config import Config
from aggregator import ActivityAggregator
import download_report


class ReportUI(tk.Tk):
    def __init__(self, logger: ActivityLogger, config: Config):
        super().__init__()
        self.title('Activity Monitor Reports')
        self.geometry('700x420')
        self.logger = logger
        self.config = config
        self.agg = ActivityAggregator(logger, config)

        self._build()
        self._populate()

    def _build(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=12, pady=12)

        self.tree = ttk.Treeview(frm, columns=('name', 'modified'), show='headings')
        self.tree.heading('name', text='Report')
        self.tree.heading('modified', text='Modified')
        self.tree.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=8)

        self.btn_refresh = ttk.Button(btn_frame, text='Refresh', command=self._populate)
        self.btn_refresh.pack(side='left')

        self.btn_regen = ttk.Button(btn_frame, text='Regenerate Latest', command=self._regen_latest)
        self.btn_regen.pack(side='left', padx=6)

        self.btn_download = ttk.Button(btn_frame, text='Copy to Downloads', command=self._copy_selected)
        self.btn_download.pack(side='left', padx=6)

        self.btn_open_folder = ttk.Button(btn_frame, text='Open Reports Folder', command=self._open_reports_folder)
        self.btn_open_folder.pack(side='right')

    def _populate(self):
        reports_dir = Path(self.logger.logs_dir) / 'reports'
        self.tree.delete(*self.tree.get_children())
        if not reports_dir.exists():
            return
        for p in sorted(reports_dir.glob('*.pdf'), key=lambda x: x.stat().st_mtime, reverse=True):
            self.tree.insert('', 'end', values=(p.name, p.stat().st_mtime))

    def _regen_latest(self):
        def worker():
            self.btn_regen.config(state='disabled')
            try:
                path = self.agg.save_weekly_report_pdf()
                if path:
                    messagebox.showinfo('Regenerate', f'Regenerated: {path}')
                else:
                    messagebox.showerror('Regenerate', 'Failed to regenerate report')
            finally:
                self.btn_regen.config(state='normal')
                self._populate()

        threading.Thread(target=worker, daemon=True).start()

    def _copy_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Download', 'Select a report first')
            return
        name = self.tree.item(sel[0])['values'][0]
        reports_dir = Path(self.logger.logs_dir) / 'reports'
        src = reports_dir / name
        if not src.exists():
            messagebox.showerror('Download', 'Selected file not found')
            return
        dest = download_report.copy_to_downloads(src)
        messagebox.showinfo('Download', f'Copied to: {dest}')

    def _open_reports_folder(self):
        reports_dir = Path(self.logger.logs_dir) / 'reports'
        if reports_dir.exists():
            download_report.reveal_in_explorer(reports_dir)


def main():
    cfg = Config.from_env()
    logger = ActivityLogger(cfg)
    app = ReportUI(logger, cfg)
    app.mainloop()


if __name__ == '__main__':
    main()
