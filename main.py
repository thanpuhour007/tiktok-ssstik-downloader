import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from playwright.sync_api import sync_playwright
import threading
import queue


class DownloadStatus:
    def __init__(self, url):
        self.url = url
        self.status = "Pending"
        self.progress = 0

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        window_width = 800
        window_height = 920
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.download_queue = queue.Queue()
        self.status_dict = {}
        self.failed_urls = []
        self.setup_ui()

    def setup_ui(self):
        # Frame for URL entry
        url_frame = tk.Frame(self.root)
        url_frame.pack(fill="x", padx=10, pady=5)

        url_label = tk.Label(url_frame, text="Enter URLs:")
        url_label.pack(side="left")

        self.url_entry = tk.Text(url_frame, height=18, width=80)
        self.url_entry.pack(side="left", fill="x", expand=True)

        # Frame for Failed URLs
        failed_frame = tk.Frame(self.root)
        failed_frame.pack(fill="x", padx=10, pady=5)

        failed_label = tk.Label(failed_frame, text="Failed URLs:")
        failed_label.pack(side="left")

        self.failed_urls_text = tk.Text(failed_frame, height=5, bg='#ffeded')
        self.failed_urls_text.pack(side="left", fill="x", expand=True)

        # Frame for Directory Selection
        dir_frame = tk.Frame(self.root)
        dir_frame.pack(fill="x", padx=10, pady=5)

        dir_label = tk.Label(dir_frame, text="Select Download Directory:")
        dir_label.pack(side="left")

        self.dir_entry = tk.Entry(dir_frame, width=50)
        self.dir_entry.pack(side="left", fill="x", expand=True)

        dir_button = tk.Button(dir_frame, text="Browse", command=self.select_directory)
        dir_button.pack(side="left", padx=5)

        # Frame for Overall Progress
        overall_frame = tk.Frame(self.root)
        overall_frame.pack(fill="x", padx=10, pady=5)

        overall_label = tk.Label(overall_frame, text="Overall Progress:")
        overall_label.pack(side="left")

        self.overall_progress = ttk.Progressbar(
            overall_frame, orient="horizontal", length=200, mode="determinate"
        )
        self.overall_progress.pack(side="left", padx=5, fill="x", expand=True)

        # Frame for Status List
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create a canvas with scrollbar for the status list
        canvas = tk.Canvas(status_frame)
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=canvas.yview)
        self.status_list_frame = tk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas.create_window((0, 0), window=self.status_list_frame, anchor="nw")
        self.status_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        buttons_frame = tk.Frame(self.root)
        buttons_frame.pack(fill="x", padx=10, pady=10)

        self.retry_button = tk.Button(
            buttons_frame, text="Retry Failed URLs", command=self.retry_failed_urls, state="disabled"
        )
        self.retry_button.pack(side="left", padx=5)

        self.clear_button = tk.Button(
            buttons_frame, text="Clear All", command=self.clear_all
        )
        self.clear_button.pack(side="left", padx=5)

        self.start_button = tk.Button(
            buttons_frame, text="Start Download", command=self.start_download
        )
        self.start_button.pack(side="left", padx=5)

        credit_label = tk.Label(self.root, text="Credit by: Than Pu Hour Dev")
        credit_label.pack(side="bottom", pady=10)

    def clear_all(self):
        self.url_entry.delete("1.0", tk.END)
        self.failed_urls_text.delete("1.0", tk.END)
        self.failed_urls = []
        for widget in self.status_list_frame.winfo_children():
            widget.destroy()
        self.status_dict.clear()
        self.overall_progress["value"] = 0
        self.retry_button.config(state="disabled")

    def select_directory(self):
        download_dir = filedialog.askdirectory()
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, download_dir)

    def update_status(self, url, status, progress=None):
        if url not in self.status_dict:
            frame = tk.Frame(self.status_list_frame)
            frame.pack(fill="x", pady=2)

            url_label = tk.Label(frame, text=url[:30] + "...", width=30, anchor="w")
            url_label.pack(side="left", padx=5)

            status_label = tk.Label(frame, text=status, width=15)
            status_label.pack(side="left", padx=5)

            progress_bar = ttk.Progressbar(
                frame, orient="horizontal", length=150, mode="determinate"
            )
            progress_bar.pack(side="left", padx=5)

            self.status_dict[url] = {
                "frame": frame,
                "status_label": status_label,
                "progress_bar": progress_bar
            }
        else:
            self.status_dict[url]["status_label"].config(text=status)
            if progress is not None:
                self.status_dict[url]["progress_bar"]["value"] = progress

        self.root.update_idletasks()

    def add_to_failed_urls(self, url):
        if url not in self.failed_urls:
            self.failed_urls.append(url)
            self.failed_urls_text.delete("1.0", tk.END)
            for failed_url in self.failed_urls:
                self.failed_urls_text.insert(tk.END, failed_url + "\n")
            self.retry_button.config(state="normal")

    def download_video(self, url, download_dir):
        try:
            self.update_status(url, "Starting...")

            def run(playwright):
                browser = playwright.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()

                self.update_status(url, "Loading page...", 20)
                page.goto("https://ssstik.io/")

                self.update_status(url, "Entering URL...", 40)
                page.get_by_placeholder("Just insert a link").fill(url)
                page.get_by_role("button", name="Download").click()

                self.update_status(url, "Downloading...", 60)
                with page.expect_download() as download_info:
                    page.get_by_text("Without watermark HD", exact=True).click()
                download = download_info.value

                self.update_status(url, "Saving file...", 80)
                download.save_as(os.path.join(download_dir, download.suggested_filename))

                context.close()
                browser.close()

                self.update_status(url, "Complete", 100)
                if url in self.failed_urls:
                    self.failed_urls.remove(url)
                    self.failed_urls_text.delete("1.0", tk.END)
                    for failed_url in self.failed_urls:
                        self.failed_urls_text.insert(tk.END, failed_url + "\n")
                    if not self.failed_urls:
                        self.retry_button.config(state="disabled")

            with sync_playwright() as playwright:
                run(playwright)

        except Exception as e:
            self.update_status(url, f"Error: {str(e)}", 0)
            self.add_to_failed_urls(url)

    def retry_failed_urls(self):
        if not self.failed_urls:
            return

        download_dir = self.dir_entry.get()
        if not download_dir:
            messagebox.showerror("Error", "Please select a download directory.")
            return

        # Copy failed URLs and clear the list
        urls_to_retry = self.failed_urls.copy()
        self.failed_urls = []
        self.failed_urls_text.delete("1.0", tk.END)

        def retry_thread():
            total_urls = len(urls_to_retry)
            for i, url in enumerate(urls_to_retry, 1):
                self.download_video(url.strip(), download_dir)
                self.overall_progress["value"] = (i / total_urls) * 100
                self.root.update_idletasks()

            if not self.failed_urls:
                messagebox.showinfo("Success", "All retry attempts completed.")
            self.start_button.config(state="normal")

        self.start_button.config(state="disabled")
        threading.Thread(target=retry_thread, daemon=True).start()

    def start_download(self):
        urls = self.url_entry.get("1.0", tk.END).strip().split("\n")
        download_dir = self.dir_entry.get()

        if not urls or not download_dir:
            messagebox.showerror("Error", "Please enter URLs and select a download directory.")
            return

        # Clear previous status entries
        for widget in self.status_list_frame.winfo_children():
            widget.destroy()
        self.status_dict.clear()

        # Reset overall progress
        self.overall_progress["value"] = 0
        total_urls = len(urls)

        def download_thread():
            for i, url in enumerate(urls, 1):
                if url.strip():
                    self.download_video(url.strip(), download_dir)
                    self.overall_progress["value"] = (i / total_urls) * 100
                    self.root.update_idletasks()

            if not self.failed_urls:
                messagebox.showinfo("Success", "All videos have been processed.")
            else:
                messagebox.showwarning("Warning",
                                       f"{len(self.failed_urls)} downloads failed. Check the Failed URLs section.")
            self.start_button.config(state="normal")

        self.start_button.config(state="disabled")
        threading.Thread(target=download_thread, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()