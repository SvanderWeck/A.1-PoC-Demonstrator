import os
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy

from bs4 import BeautifulSoup
import pandas as pd
import glob
import warnings

warnings.filterwarnings('ignore')
warnings.warn('DelftStack')
warnings.warn('Do not show this message')

UPLOAD_FOLDER = 'C:\\Users\\vanderweck\\PycharmProjects\\Masterarbeit\\Systemmodelle\\NewModel'  # DO: Add path to folder where new models are stored
ALLOWED_EXTENSIONS = {'xmi'}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
@app.route('/homepage')
def homepage():
    return render_template('home.html')


@app.route('/funktionsweise')
def funktionsweise():
    return render_template('funktionsweise.html')


# send data from this route to html
# to access we need jinja, special web syntax to access through html
@app.route('/upload')
def upload():
    return render_template('upload.html')


@app.route('/uploader', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            def extract_model_from_file(content):
                '''
                Extracts model, context values and if exists the error description from xmi file.

                        Parameters:
                                model_file (TextIOWrapper): xmi file containing the model

                        Returns:
                                binary_sum (Dict): Model with context and error code
                '''
                model = {}

                # split file string into model and error code
                model_file = content[:content.index('</uml:Model>') + len('</uml:Model>')] + '\n' + '</xmi:XMI>'
                model_file = model_file.replace('\n', '')
                error_code = content[content.index('</uml:Model>') + len('</uml:Model>'):]

                # extract error description
                if 'Fehler' in error_code:
                    model['is_error'] = 1
                    error_code_lines = error_code.split("\n")
                    for i, line in enumerate(error_code_lines):
                        if 'Fehler' in line:
                            error_description = line.partition('TAG_02_Fehlerbeschreibung = "')[2][0:-4]
                            model['error_description'] = error_description
                else:
                    model['is_error'] = 0
                    model['error_description'] = 'Fehlerfreies Referenzmodell'

                # extract model name
                soup = BeautifulSoup(model_file, 'lxml')
                model_name = soup.packagedelement['name']
                model['model_name'] = model_name

                # extract model parameters and context variables
                for part in soup.packagedelement.packagedelement.find_all(True):
                    part_id = part['type']
                    part_name = soup.find('packagedelement', {'xmi:id': part_id})['name']
                    part_category = soup.find('packagedelement', {'xmi:id': part_id}).parent['name']
                    model[part_category] = part_name

                return model

            def compare_new_model_to_known(new_model, known_models):
                '''
                Compare one model to all known models and calculate congruencies.

                        Parameters:
                                new_model (Dict): model that should be compared
                                known_models (DataFrame): models that are already known

                        Returns:
                                congruency (Dict): Congruencies with all models the new model was compared with
                '''
                known_models = known_models.reset_index().drop(
                    columns='index')  # make sure indexes pair with number of rows
                congruency = {}
                parameters = ['01_Rahmenlängsträger', '02_Rahmenquerträger', '03_1. Vorderachse', '04_1. Hinterachse',
                              '05_Federung VA', '06_Federung HA', '07_Motor', '07_SW_Motor', '08_Getriebe',
                              '08_SW_Getriebe',
                              '09_Fahrerhaus']
                for index, row in known_models.iterrows():
                    count = 0
                    for col in known_models.columns.to_list():
                        if col in parameters:
                            if row[col] == new_model[col]:
                                count += 1
                    congruency[index] = count / 11
                return congruency

            # create table for models
            column_names = ['model_name', '01_Rahmenlängsträger', '02_Rahmenquerträger', '03_1. Vorderachse',
                            '04_1. Hinterachse',
                            '05_Federung VA', '06_Federung HA', '07_Motor', '07_SW_Motor', '08_Getriebe',
                            '08_SW_Getriebe',
                            '09_Fahrerhaus', '01_Aussentemperatur', '02_Luftfeuchtigkeit', '03_Motordrehzahl']
            df_models = pd.DataFrame(columns=column_names)

            path_to_xmi_files = 'C:\\Users\\vanderweck\\PycharmProjects\\Masterarbeit\\Systemmodelle\\OldModels\\'  # DO: If the files are not in the same folder as the code file, add path to file.
            file_names = [f for f in glob.glob(path_to_xmi_files + "*.xmi")]
            # print(file_names)

            for file_name in file_names:
                # print(file_name)
                with open(file_name, 'r') as file:
                    content = file.read()
                # print(file)
                model = extract_model_from_file(content)
                df_models = df_models.append(model, ignore_index=True)
                # print(model)

            # read new model
            path_to_new_xmi_file = 'C:\\Users\\vanderweck\\PycharmProjects\\Masterarbeit\\Systemmodelle\\NewModel\\'
            new_files = [f for f in glob.glob(path_to_new_xmi_file + "*.xmi")]

            for new_file in new_files:
                # print(file_name)
                with open(new_file, 'r') as file:
                    content = file.read()

            new_model = extract_model_from_file(content)
            congruencies = compare_new_model_to_known(new_model, df_models)
            # print(new_model)

            # find congruencies
            highest_congruency = 0
            hc_model = 0  # Model with highest congruency
            for model in congruencies:
                if highest_congruency < congruencies[model]:
                    highest_congruency = congruencies[model]
                    hc_model = model

            b = df_models.loc[hc_model].model_name
            c = str(round(highest_congruency, 2) * 100)
            d = str(df_models.loc[hc_model].is_error)
            e = df_models.loc[hc_model].error_description
            g = df_models.loc[hc_model]['01_Aussentemperatur']
            h = df_models.loc[hc_model]['03_Motordrehzahl']
            i = df_models.loc[hc_model]['02_Luftfeuchtigkeit']

            if df_models.loc[hc_model].is_error == 0.0:
                return render_template('return_positive_results.html', b=b, c=c, g=g, h=h, i=i)
            else:
                return render_template('return_negative_results.html', b=b, c=c, e=e, g=g, h=h, i=i)


if __name__ == '__main__':
    app.debug = True
    app.run()
