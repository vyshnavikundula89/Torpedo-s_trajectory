from flask import Flask, render_template, request, session, redirect, url_for
import os
import pandas as pd
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.palettes import Category10
from bokeh.resources import CDN

app = Flask(__name__)
app.secret_key = "your_secret_key"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_column_count(files_data):
    """Returns the number of columns from the first uploaded CSV (if available)"""
    if files_data:
        filepath = files_data[0]["path"]
        try:
            df = pd.read_csv(filepath)
            return len(df.columns)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    if "files_data" not in session:
        session["files_data"] = []

    selected_column_index = session.get("selected_column_index", None)

    if request.method == "POST":
        if "files[]" in request.files:
            files = request.files.getlist("files[]")
            for file in files:
                if file and file.filename.endswith(".csv"):
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                    file.save(filepath)
                    session["files_data"].append({"name": file.filename, "path": filepath})
            session.modified = True
            return redirect(url_for("index"))

        if "clear_all" in request.form:
            session["files_data"] = []
            session["selected_column_index"] = None
            session.modified = True
            return redirect(url_for("index"))

        if "remove_file" in request.form:
            filename = request.form["remove_file"]
            session["files_data"] = [file for file in session["files_data"] if file["name"] != filename]
            session.modified = True
            return redirect(url_for("index"))

        if "select_column" in request.form:
            try:
                selected_column_index = int(request.form["column_index"])
                column_count = get_column_count(session["files_data"])

                if column_count is not None and 0 <= selected_column_index < column_count:
                    session["selected_column_index"] = selected_column_index
                else:
                    session["selected_column_index"] = None
            except ValueError:
                session["selected_column_index"] = None

            session.modified = True

    column_count = get_column_count(session["files_data"])
    same_columns = column_count is not None
    column_range = f"0 to {column_count - 1}" if same_columns else None

    return render_template("index.html", files_data=session["files_data"], same_columns=same_columns, column_range=column_range, selected_column_index=selected_column_index)

@app.route("/graph")
def graph():
    if "files_data" not in session or not session["files_data"]:
        return "<h2>No data available to plot. Please upload a CSV file first.</h2>"

    column_count = get_column_count(session["files_data"])
    if column_count is None:
        return "<h2>Uploaded files have different numbers of columns. Please upload files with the same structure.</h2>"

    selected_column_index = session.get("selected_column_index", None)
    if selected_column_index is None:
        return "<h2>No column index selected. Please enter a valid column index before plotting.</h2>"

    dfs = []
    for file_info in session["files_data"]:
        filepath = file_info["path"]
        try:
            df = pd.read_csv(filepath)
            if not df.empty and 0 <= selected_column_index < len(df.columns):
                column_name = df.columns[selected_column_index]
                column_data = df[column_name]
                if column_data.dtype in ["float64", "int64"]:
                    dfs.append((file_info["name"], column_data))
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    if not dfs:
        return "<h2>No numeric data found in the selected column.</h2>"

    p = figure(title="CSV Column Comparison", x_axis_label="Index", y_axis_label="Values", width=1000, height=600)
    colors = Category10[len(dfs)]

    for (name, column_data), color in zip(dfs, colors):
        source = ColumnDataSource(data={"x": list(range(len(column_data))), "y": column_data.tolist()})
        p.line("x", "y", source=source, legend_label=name, line_width=2, color=color)
        p.circle("x", "y", source=source, size=6, color=color, legend_label=name)
    

    script, div = components(p)
    return render_template("graph.html", script=script, div=div, cdn_js=CDN.render())

if __name__ == "__main__":
    app.run(debug=True)
