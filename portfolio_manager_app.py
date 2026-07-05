from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from portfolio_generator import PortfolioProject, CaseStudySection, add_project_to_portfolio, slugify

APP_TITLE = "Topium Portfolio Manager"


class PortfolioManagerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1080x760")
        self.minsize(940, 680)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.portfolio_folder = tk.StringVar()
        self.cover_image = tk.StringVar()
        self.title_var = tk.StringVar()
        self.slug_var = tk.StringVar()
        self.category_var = tk.StringVar(value="Static site tooling / desktop app")
        self.status_var = tk.StringVar(value="Prototype")
        self.github_url_var = tk.StringVar()
        self.tech_stack_var = tk.StringVar(value="Python, customtkinter, PyInstaller, HTML generation, static site automation")

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="Topium Portfolio Manager", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=22, pady=(16, 4), sticky="w"
        )
        ctk.CTkLabel(
            header,
            text="Generate project cards and full case-study pages without manually editing HTML.",
            text_color=("gray25", "gray70"),
        ).grid(row=1, column=0, padx=22, pady=(0, 16), sticky="w")

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, padx=18, pady=18, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(footer, text="Ready", anchor="w")
        self.status_label.grid(row=0, column=0, padx=22, pady=12, sticky="ew")
        ctk.CTkButton(footer, text="Preview JSON", command=self.preview_json, width=130).grid(row=0, column=1, padx=(0, 10), pady=10)
        ctk.CTkButton(footer, text="Generate Project", command=self.generate_project, width=160).grid(row=0, column=2, padx=(0, 22), pady=10)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        left = ctk.CTkFrame(parent)
        left.grid(row=0, column=0, rowspan=2, padx=(14, 7), pady=14, sticky="nsew")
        left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Project basics", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(16, 10), sticky="w"
        )

        self._row(left, 1, "Portfolio folder", self.portfolio_folder, self.pick_portfolio_folder)
        self._row(left, 2, "Cover image", self.cover_image, self.pick_cover_image)
        self._entry(left, 3, "Project title", self.title_var)
        self._entry(left, 4, "Slug", self.slug_var)
        self._entry(left, 5, "Category", self.category_var)
        self._entry(left, 6, "Status", self.status_var)
        self._entry(left, 7, "GitHub link", self.github_url_var)
        self._entry(left, 8, "Tech stack", self.tech_stack_var)

        ctk.CTkLabel(left, text="Short description").grid(row=9, column=0, columnspan=3, padx=16, pady=(14, 6), sticky="w")
        self.description_text = ctk.CTkTextbox(left, height=96)
        self.description_text.grid(row=10, column=0, columnspan=3, padx=16, pady=(0, 14), sticky="ew")
        self.description_text.insert(
            "1.0",
            "A local desktop content-management tool for maintaining a static portfolio. It generates project cards, copies cover assets, and builds full case-study pages from structured inputs.",
        )

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        right = ctk.CTkFrame(parent)
        right.grid(row=0, column=1, rowspan=2, padx=(7, 14), pady=14, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(right, text="Case study sections", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 10), sticky="w"
        )
        self.sections_text = ctk.CTkTextbox(right)
        self.sections_text.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="nsew")
        self.sections_text.insert(
            "1.0",
            "Problem:\nAdding new work to a static HTML portfolio can become slow, repetitive, and easy to break.\n\n"
            "Build:\n- Select the portfolio folder.\n- Enter project metadata.\n- Pick a cover image.\n- Write case-study sections.\n- Generate the gallery card and full project page.\n\n"
            "What it shows:\nThis project shows desktop UI design, filesystem automation, static site generation, and practical tooling built for a real workflow.\n\n"
            "Next version:\n- Live preview panel.\n- Edit existing projects.\n- Git commit button.\n- Drag-and-drop cover images.\n",
        )

    def _row(self, parent: ctk.CTkFrame, row: int, label: str, variable: tk.StringVar, command) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=16, pady=7, sticky="w")
        ctk.CTkEntry(parent, textvariable=variable).grid(row=row, column=1, padx=8, pady=7, sticky="ew")
        ctk.CTkButton(parent, text="Browse", width=78, command=command).grid(row=row, column=2, padx=(0, 16), pady=7)

    def _entry(self, parent: ctk.CTkFrame, row: int, label: str, variable: tk.StringVar) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=16, pady=7, sticky="w")
        entry = ctk.CTkEntry(parent, textvariable=variable)
        entry.grid(row=row, column=1, columnspan=2, padx=(8, 16), pady=7, sticky="ew")
        if label == "Project title":
            entry.bind("<FocusOut>", self.autofill_slug)

    def pick_portfolio_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select your portfolio repo folder")
        if folder:
            self.portfolio_folder.set(folder)

    def pick_cover_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose cover image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.svg"), ("All files", "*.*")],
        )
        if path:
            self.cover_image.set(path)

    def autofill_slug(self, _event=None) -> None:
        if self.title_var.get().strip() and not self.slug_var.get().strip():
            self.slug_var.set(slugify(self.title_var.get()))

    def parse_sections(self) -> list[CaseStudySection]:
        raw = self.sections_text.get("1.0", "end").strip()
        sections: list[CaseStudySection] = []
        current_heading = "Overview"
        current_lines: list[str] = []

        def flush() -> None:
            nonlocal current_lines, current_heading
            if not current_heading and not current_lines:
                return
            bullets = [line[2:].strip() for line in current_lines if line.strip().startswith("- ")]
            body_lines = [line.strip() for line in current_lines if line.strip() and not line.strip().startswith("- ")]
            sections.append(CaseStudySection(current_heading, " ".join(body_lines), bullets))
            current_lines = []

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.endswith(":") and stripped[:-1] and not stripped.startswith("-"):
                flush()
                current_heading = stripped[:-1]
            else:
                current_lines.append(line)
        flush()
        return [section for section in sections if section.heading or section.body or section.bullets]

    def build_project(self) -> PortfolioProject:
        self.autofill_slug()
        tech_stack = [item.strip() for item in self.tech_stack_var.get().split(",") if item.strip()]
        return PortfolioProject(
            title=self.title_var.get().strip(),
            slug=self.slug_var.get().strip(),
            category=self.category_var.get().strip(),
            status=self.status_var.get().strip(),
            description=self.description_text.get("1.0", "end").strip(),
            cover_image=self.cover_image.get().strip(),
            github_url=self.github_url_var.get().strip(),
            tech_stack=tech_stack,
            sections=self.parse_sections(),
        )

    def preview_json(self) -> None:
        project = self.build_project()
        data = {
            "title": project.title,
            "slug": project.slug,
            "category": project.category,
            "status": project.status,
            "description": project.description,
            "cover_image": project.cover_image,
            "github_url": project.github_url,
            "tech_stack": project.tech_stack,
            "sections": [section.__dict__ for section in project.sections],
        }
        preview = ctk.CTkToplevel(self)
        preview.title("Project JSON Preview")
        preview.geometry("760x560")
        box = ctk.CTkTextbox(preview)
        box.pack(fill="both", expand=True, padx=14, pady=14)
        box.insert("1.0", json.dumps(data, indent=2))

    def generate_project(self) -> None:
        try:
            folder = Path(self.portfolio_folder.get().strip())
            if not folder.exists():
                raise FileNotFoundError("Select a valid portfolio folder first.")

            project = self.build_project()
            result = add_project_to_portfolio(folder, project)
            self.status_label.configure(text=f"Generated: projects/{result['slug']}/index.html")
            messagebox.showinfo(APP_TITLE, "Project generated successfully. Check your portfolio folder.")
        except Exception as exc:
            self.status_label.configure(text=f"Error: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))


def main() -> None:
    app = PortfolioManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
