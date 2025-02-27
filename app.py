from flask import Flask, render_template, request, session, redirect, url_for
import os
import pandas as pd
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.resources import CDN

app = Flask(__name__)
app.secret_key = "your_secret_key"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_column_counts(files_data):
    """Returns a set of column counts from all uploaded CSV files"""
    column_counts = set()
    for file_info in files_data:
        filepath = file_info["path"]
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                if not df.empty:
                    column_counts.add(len(df.columns))
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    return column_counts

@app.route("/", methods=["GET", "POST"])
def index():
    if "files_data" not in session:
        session["files_data"] = []

    global_column = 1  

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
            session.modified = True
            return redirect(url_for("index"))

        if "remove_file" in request.form:
            filename = request.form["remove_file"]
            session["files_data"] = [file for file in session["files_data"] if file["name"] != filename]
            session.modified = True
            return redirect(url_for("index"))

        if "update_all_columns" in request.form:
            try:
                global_column = int(request.form["column"]) - 1  
            except ValueError:
                global_column = 0  

    column_counts = get_column_counts(session["files_data"])
    same_columns = len(column_counts) == 1  

    return render_template("index.html", files_data=session["files_data"], same_columns=same_columns, global_column=global_column)

@app.route("/graph")
def graph():
    if "files_data" not in session or not session["files_data"]:
        return "<h2>No data available to plot. Please upload a CSV file first.</h2>"

    column_counts = get_column_counts(session["files_data"])
    
    if len(column_counts) != 1:
        return "<h2>Uploaded files have different numbers of columns. Please upload files with the same structure.</h2>"

    dfs = []
    global_column = 1  

    for file_info in session["files_data"]:
        filepath = file_info["path"]
        try:
            df = pd.read_csv(filepath)
            if not df.empty and global_column < len(df.columns):
                column_data = df.iloc[:, global_column]
                if column_data.dtype in ["float64", "int64"]:
                    dfs.append((file_info["name"], column_data))
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    if not dfs:
        return "<h2>No numeric data found in uploaded files.</h2>"

    p = figure(title="CSV Column Comparison", x_axis_label="Index", y_axis_label="Values", width=1000, height=600)

    for name, column_data in dfs:
        source = ColumnDataSource(data={"x": list(range(len(column_data))), "y": column_data.tolist()})
        p.line("x", "y", source=source, legend_label=name, line_width=2)
        p.circle("x", "y", source=source, size=6, color="red", legend_label=name)

    script, div = components(p)
    return render_template("graph.html", script=script, div=div, cdn_js=CDN.render())

if __name__ == "__main__":
    app.run(debug=True)
