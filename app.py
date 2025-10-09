import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, callback
import numpy as np
import io
import base64
from weasyprint import HTML, CSS
import tempfile

# --- Configuration Dash ---
app = Dash(__name__, suppress_callback_exceptions=True)

# --- Chemins et configuration des données ---
CSV_FILE = 'data/monfiche.csv'
CSV_DELIMITER = ';'
CSV_ENCODING = 'utf-8'

# --- Nettoyage et préparation des données avec Pandas ---
def load_and_prepare_data(file_path, delimiter, encoding):
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            print(f"Le fichier {file_path} est introuvable ou vide. Retourne un DataFrame vide.")
            return pd.DataFrame()

        df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding)

        # Impression pour le débogage: Affiche les noms de colonnes BRUTS après lecture
        print("Colonnes lues après pd.read_csv :", df.columns.tolist())

        # Carte de renommage des colonnes (avec les dernières corrections précises)
        column_rename_map = {
            'Numero du formulaire': 'ID_Formulaire',
            'responsable': 'Responsable',
            'Numero WhatsApp': 'WhatsApp',
            'wilaya': 'Wilaya',
            'Commune': 'Commune',
            'Point de vaccination': 'Point_Vaccination',
            'Localisation GPS du point': 'Localisation_GPS_Complete',
            '_Localisation GPS du point_latitude': 'Latitude',
            '_Localisation GPS du point_longitude': 'Longitude',
            '_Localisation GPS du point_altitude': 'Altitude',
            '_Localisation GPS du point_precision': 'Precision_GPS',
            'Population approximative': 'Population_Approx',
            "Nombre d'enfants en age de vaccination": 'Enfants_Age_Vaccination',
            'enfants zero dose': 'Enfants_Zero_Dose',
            # Corrections pour correspondre exactement à la dernière sortie console
            'Source energie de unite': 'Source_Energie',
            'Avez-vous le calendrier vaccinal ': 'Calendrier_Vaccinal', # Retiré le '?'
            'Quels indicateurs de vaccination connaissez-vous ': 'Indicateurs_Connus', # Retiré le '?'
            'Quels sont les principaux defis que vous rencontrez ': 'Defis_Principaux', # Retiré le '?' et l'accent
            'Quelles sont vos propositions de solutions ?': 'Propositions_Solutions',
        }

        # Filtrer la map pour ne renommer que les colonnes existantes
        df = df.rename(columns={k: v for k, v in column_rename_map.items() if k in df.columns})

        # Impression pour le débogage: Affiche les noms de colonnes APRÈS renommage
        print("Colonnes après renommage :", df.columns.tolist())

        if 'Localisation_GPS_Complete' in df.columns and 'Latitude' in df.columns:
            df = df.drop(columns=['Localisation_GPS_Complete'])

        numeric_cols = ['Latitude', 'Longitude', 'Altitude', 'Precision_GPS',
                        'Population_Approx', 'Enfants_Age_Vaccination', 'Enfants_Zero_Dose']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            df = df[df['Latitude'] != 0].copy()
            df = df[df['Longitude'] != 0].copy()

        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # Nettoyage spécifique pour Point_Vaccination (pour s'assurer qu'il est bien string)
        if 'Point_Vaccination' in df.columns:
            df['Point_Vaccination'] = df['Point_Vaccination'].astype(str).replace('', 'Non spécifié Point').fillna('Non spécifié Point')

        # Nettoyage des colonnes pour les listes déroulantes
        if 'Wilaya' in df.columns:
            df['Wilaya'] = df['Wilaya'].fillna('Non spécifié').replace('', 'Non spécifié')
        if 'Commune' in df.columns:
            df['Commune'] = df['Commune'].fillna('Non spécifié').replace('', 'Non spécifié')
        if 'Source_Energie' in df.columns:
            df['Source_Energie'] = df['Source_Energie'].fillna('Non spécifié').replace('', 'Non spécifié')

        if 'Point_Vaccination' in df.columns:
            df['Total_Points_Vaccination'] = 1

        print(f"DataFrame chargé et préparé. Nombre de lignes : {len(df)}")
        return df

    except Exception as e:
        print(f"Erreur lors du chargement ou de la préparation des données : {e}")
        return pd.DataFrame()

df_global = load_and_prepare_data(CSV_FILE, CSV_DELIMITER, CSV_ENCODING)

# Message de débogage mis à jour pour être plus spécifique
if df_global.empty:
    print("DataFrame est vide après la tentative de chargement. Veuillez vérifier le fichier CSV, son chemin ('data/monficher.csv'), le délimiteur (';') et l'encodage ('utf-8'). Examinez également les messages d'erreur dans la console si le chargement a échoué.")
    df_global = pd.DataFrame(columns=[
        'Wilaya', 'Commune', 'Point_Vaccination', 'Responsable',
        'Enfants_Zero_Dose', 'Enfants_Age_Vaccination', 'Latitude', 'Longitude',
        'Source_Energie', 'Calendrier_Vaccinal', 'Defis_Principaux', 'Propositions_Solutions'
    ])

# Les options des filtres sont générées à partir de df_global, donc elles dépendent des données chargées
wilaya_options = [{'label': i, 'value': i} for i in sorted(df_global['Wilaya'].unique()) if pd.notna(i) and i != 'Non spécifié'] if 'Wilaya' in df_global.columns else []
commune_options = [{'label': i, 'value': i} for i in sorted(df_global['Commune'].unique()) if pd.notna(i) and i != 'Non spécifié'] if 'Commune' in df_global.columns else []
source_energie_options = [{'label': i, 'value': i} for i in sorted(df_global['Source_Energie'].unique()) if pd.notna(i) and i != 'Non spécifié'] if 'Source_Energie' in df_global.columns else []


# --- Layout de l'application Dash (HTML) ---
app.layout = html.Div(children=[
    html.Nav(className='navbar navbar-expand-lg navbar-dark bg-dark', children=[
        html.Div(className='container-fluid', children=[
            html.A('Tableau de Bord Vaccination', className='navbar-brand', href='#'),
        ])
    ], style={'padding': '10px 0'}),

    html.Div(className='container-fluid mt-4', children=[
        html.H1('Données de l\'Enquête de Vaccination', className='mb-4 text-center'),

        html.Div(className='row mb-4', children=[
            html.Div(className='col-md-3', children=[
                html.Div(className='card text-center p-3', children=[
                    html.H5('Points de Vaccination', className='card-title'),
                    html.P(id='kpi-total-points', className='card-text fs-2')
                ])
            ]),
            html.Div(className='col-md-3', children=[
                html.Div(className='card text-center p-3', children=[
                    html.H5('Enfants Zéro Dose (Total)', className='card-title'),
                    html.P(id='kpi-zero-dose', className='card-text fs-2')
                ])
            ]),
            html.Div(className='col-md-3', children=[
                html.Div(className='card text-center p-3', children=[
                    html.H5('Enfants en Âge de Vaccination (Total)', className='card-title'),
                    html.P(id='kpi-age-vaccination', className='card-text fs-2')
                ])
            ]),
            html.Div(className='col-md-3', children=[
                html.Div(className='card text-center p-3', children=[
                    html.H5('Pourcentage Zéro Dose', className='card-title'),
                    html.P(id='kpi-percent-zero-dose', className='card-text fs-2')
                ])
            ]),
        ]),

        html.Div(className='row mb-4', children=[
            html.Div(className='col-md-4', children=[
                html.Label('Sélectionner Wilaya:', style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='dropdown-wilaya',
                    options=wilaya_options,
                    multi=True,
                    placeholder="Toutes les Wilayas"
                )
            ]),
            html.Div(className='col-md-4', children=[
                html.Label('Sélectionner Commune:', style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='dropdown-commune',
                    options=commune_options,
                    multi=True,
                    placeholder="Toutes les Communes"
                )
            ]),
             html.Div(className='col-md-4', children=[
                html.Label('Source d\'Énergie:', style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='dropdown-source-energie',
                    options=source_energie_options,
                    multi=True,
                    placeholder="Toutes les Sources"
                )
            ]),
        ]),

        html.Div(className='row', children=[
            html.Div(className='col-md-6 mb-4', children=[
                html.Div(className='card p-3', children=[
                    html.H5('Carte des Points de Vaccination', className='card-title text-center'),
                    dcc.Graph(id='map-vaccination-points', style={'height': '400px'})
                ])
            ]),
            html.Div(className='col-md-6 mb-4', children=[
                html.Div(className='card p-3', children=[
                    html.H5('Enfants Zéro Dose par Commune', className='card-title text-center'),
                    dcc.Graph(id='enfants-zero-dose-chart', style={'height': '400px'})
                ])
            ]),
        ]),

        html.Div(className='row', children=[
            html.Div(className='col-md-6 mb-4', children=[
                html.Div(className='card p-3', children=[
                    html.H5('Connaissance du Calendrier Vaccinal', className='card-title text-center'),
                    dcc.Graph(id='calendrier-vaccinal-chart', style={'height': '300px'})
                ])
            ]),
            html.Div(className='col-md-6 mb-4', children=[
                html.Div(className='card p-3', children=[
                    html.H5('Défis Principaux (Top 10)', className='card-title text-center'),
                    dcc.Graph(id='defis-chart', style={'height': '300px'})
                ])
            ]),
        ]),

        html.Div(className='row', children=[
            html.Div(className='col-12 mb-4', children=[
                html.Div(className='card p-3', children=[
                    html.H5('Données Détaillées de l\'Enquête', className='card-title text-center'),
                    html.Div(id='data-table', className='table-responsive')
                ])
            ])
        ]),

        # Ajout des boutons d'exportation
        html.Div(className='row mt-4 mb-4', children=[
            html.Div(className='col-md-6 text-center', children=[
                html.Button("Exporter en Excel", id="btn-export-excel", className="btn btn-success me-2")
            ]),
            html.Div(className='col-md-6 text-center', children=[
                html.Button("Exporter en PDF", id="btn-export-pdf", className="btn btn-danger")
            ])
        ]),

        # dcc.Download est un composant Dash invisible qui gère le téléchargement
        dcc.Download(id="download-dataframe-excel"),
        dcc.Download(id="download-pdf-report"),

    ]) # Fin du container-fluid
]) # Fin du html.Div parent


# --- Callbacks (Logique d'interactivité) ---

@app.callback(
    Output('dropdown-commune', 'options'),
    Input('dropdown-wilaya', 'value')
)
def set_commune_options(selected_wilayas):
    if not selected_wilayas or len(selected_wilayas) == 0:
        return [{'label': i, 'value': i} for i in sorted(df_global['Commune'].unique()) if pd.notna(i) and i != 'Non spécifié']
    else:
        filtered_df = df_global[df_global['Wilaya'].isin(selected_wilayas)]
        return [{'label': i, 'value': i} for i in sorted(filtered_df['Commune'].unique()) if pd.notna(i) and i != 'Non spécifié']


@app.callback(
    [Output('kpi-total-points', 'children'),
     Output('kpi-zero-dose', 'children'),
     Output('kpi-age-vaccination', 'children'),
     Output('kpi-percent-zero-dose', 'children'),
     Output('map-vaccination-points', 'figure'),
     Output('enfants-zero-dose-chart', 'figure'),
     Output('calendrier-vaccinal-chart', 'figure'),
     Output('defis-chart', 'figure'),
     Output('data-table', 'children')],
    [Input('dropdown-wilaya', 'value'),
     Input('dropdown-commune', 'value'),
     Input('dropdown-source-energie', 'value')]
)
def update_dashboard(selected_wilayas, selected_communes, selected_sources_energie):
    filtered_df = df_global.copy()

    if selected_wilayas and len(selected_wilayas) > 0:
        filtered_df = filtered_df[filtered_df['Wilaya'].isin(selected_wilayas)]
    if selected_communes and len(selected_communes) > 0:
        filtered_df = filtered_df[filtered_df['Commune'].isin(selected_communes)]
    if selected_sources_energie and len(selected_sources_energie) > 0:
        filtered_df = filtered_df[filtered_df['Source_Energie'].isin(selected_sources_energie)]

    # --- Calcul des KPIs ---
    total_points = filtered_df['Point_Vaccination'].nunique() if 'Point_Vaccination' in filtered_df.columns and not filtered_df.empty else 0
    total_zero_dose = filtered_df['Enfants_Zero_Dose'].sum() if 'Enfants_Zero_Dose' in filtered_df.columns and not filtered_df.empty else 0
    total_age_vaccination = filtered_df['Enfants_Age_Vaccination'].sum() if 'Enfants_Age_Vaccination' in filtered_df.columns and not filtered_df.empty else 0

    # Calcul robuste du pourcentage
    if total_age_vaccination > 0:
        percent_zero_dose_val = (total_zero_dose / total_age_vaccination * 100)
    else:
        percent_zero_dose_val = 0

    # Assurer que le pourcentage est une chaîne formatée, gérer NaN et inf
    percent_zero_dose_display = "N/A"
    if isinstance(percent_zero_dose_val, (int, float)):
        if np.isnan(percent_zero_dose_val):
            percent_zero_dose_display = "N/A"
        elif np.isinf(percent_zero_dose_val):
            percent_zero_dose_display = "Infini%"
        else:
            percent_zero_dose_display = f"{percent_zero_dose_val:.2f}%"
    elif percent_zero_dose_val is None:
        percent_zero_dose_display = "N/A"
    else:
        percent_zero_dose_display = str(percent_zero_dose_val)


    # --- Carte ---
    if 'Latitude' in filtered_df.columns and 'Longitude' in filtered_df.columns and not filtered_df.empty:
        map_fig = px.scatter_map(
            filtered_df,
            lat="Latitude",
            lon="Longitude",
            hover_name="Point_Vaccination",
            hover_data={
                "Commune": True,
                "Wilaya": True,
                "Enfants_Zero_Dose": True,
                "Latitude": False,
                "Longitude": False
            },
            color="Wilaya",
            size="Enfants_Zero_Dose",
            zoom=6,
            height=400,
            title="Points de Vaccination par Moughataa / Commune"
        )
        map_fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    else:
        map_fig = go.Figure().add_annotation(
            text="Aucune donnée de carte disponible pour la sélection.",
            xref="paper", yref="paper", showarrow=False,
            font=dict(size=16)
        )
        map_fig.update_layout(height=400)


    # --- Enfants Zéro Dose par Commune Chart ---
    if 'Commune' in filtered_df.columns and 'Enfants_Zero_Dose' in filtered_df.columns and not filtered_df.empty:
        enfants_zero_dose_commune = filtered_df.groupby('Commune')['Enfants_Zero_Dose'].sum().sort_values(ascending=False).head(10)
        enfants_zero_dose_chart_fig = px.bar(
            enfants_zero_dose_commune,
            x=enfants_zero_dose_commune.index,
            y='Enfants_Zero_Dose',
            title="Top 10 Enfants Zéro Dose par Commune",
            labels={'x': 'Commune', 'y': 'Nombre d\'enfants Zéro Dose'},
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
    else:
        enfants_zero_dose_chart_fig = go.Figure().add_annotation(text="Aucune donnée pour ce graphique.")
        enfants_zero_dose_chart_fig.update_layout(height=400)


    # --- Calendrier Vaccinal Chart ---
    if 'Calendrier_Vaccinal' in filtered_df.columns and not filtered_df.empty:
        calendrier_vaccinal_counts = filtered_df['Calendrier_Vaccinal'].value_counts()
        calendrier_vaccinal_chart_fig = px.pie(
            names=calendrier_vaccinal_counts.index,
            values=calendrier_vaccinal_counts.values,
            title="Connaissance du Calendrier Vaccinal",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        calendrier_vaccinal_chart_fig.update_traces(textinfo='percent+label')
    else:
        calendrier_vaccinal_chart_fig = go.Figure().add_annotation(text="Aucune donnée pour ce graphique.")
        calendrier_vaccinal_chart_fig.update_layout(height=300)


    # --- Défis Principaux Chart (Top 10) ---
    if 'Defis_Principaux' in filtered_df.columns and not filtered_df.empty:
        # Assurez-vous que la colonne est de type string et nettoyez les NaN/vide
        df_temp = filtered_df.copy()
        df_temp['Defis_Principaux'] = df_temp['Defis_Principaux'].astype(str).replace('', np.nan).fillna('Non spécifié')
        defis_counts = df_temp['Defis_Principaux'].value_counts().head(10)
        defis_chart_fig = px.bar(
            defis_counts,
            x=defis_counts.values,
            y=defis_counts.index,
            orientation='h',
            title="Top 10 Défis Principaux",
            labels={'x': 'Nombre d\'occurrences', 'y': 'Défi'},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        defis_chart_fig.update_yaxes(autorange="reversed")
    else:
        defis_chart_fig = go.Figure().add_annotation(text="Aucune donnée pour ce graphique.")
        defis_chart_fig.update_layout(height=300)


    # --- Génération du tableau HTML pour les données détaillées ---
    display_cols = ['Wilaya', 'Commune', 'Point_Vaccination', 'Responsable',
                    'Enfants_Zero_Dose', 'Defis_Principaux', 'Propositions_Solutions']

    existing_display_cols = [col for col in display_cols if col in filtered_df.columns]

    if not filtered_df.empty and existing_display_cols:
        table_header = [html.Th(col) for col in existing_display_cols]
        table_rows = []
        for _, row in filtered_df.iterrows():
            table_row = []
            for col in existing_display_cols:
                table_row.append(html.Td(str(row[col])))
            table_rows.append(html.Tr(table_row))

        table_html = html.Div(
            html.Table(className='table table-striped table-hover', children=[
                html.Thead(html.Tr(table_header)),
                html.Tbody(table_rows)
            ]),
            style={'maxHeight': '400px', 'overflowY': 'scroll'}
        )
    else:
        table_html = html.Div(html.P("Aucune donnée disponible pour le tableau avec la sélection actuelle."),
                              style={'textAlign': 'center', 'padding': '20px'})


    return (
        str(total_points),
        str(total_zero_dose),
        str(total_age_vaccination),
        percent_zero_dose_display,
        map_fig,
        enfants_zero_dose_chart_fig,
        calendrier_vaccinal_chart_fig,
        defis_chart_fig,
        table_html
    )

# --- Callback pour l'export Excel ---
@app.callback(
    Output("download-dataframe-excel", "data"),
    Input("btn-export-excel", "n_clicks"),
    [
        Input('dropdown-wilaya', 'value'),
        Input('dropdown-commune', 'value'),
        Input('dropdown-source-energie', 'value')
    ],
    prevent_initial_call=True,
)
def export_excel(n_clicks, selected_wilayas, selected_communes, selected_sources_energie):
    if n_clicks is None:
        return None

    # Recréer le DataFrame filtré exactement comme dans update_dashboard
    filtered_df = df_global.copy()

    if selected_wilayas and len(selected_wilayas) > 0:
        filtered_df = filtered_df[filtered_df['Wilaya'].isin(selected_wilayas)]
    if selected_communes and len(selected_communes) > 0:
        filtered_df = filtered_df[filtered_df['Commune'].isin(selected_communes)]
    if selected_sources_energie and len(selected_sources_energie) > 0:
        filtered_df = filtered_df[filtered_df['Source_Energie'].isin(selected_sources_energie)]

    # Sélectionner les colonnes pour l'exportation
    export_cols = [
        'ID_Formulaire', 'Responsable', 'WhatsApp', 'Wilaya', 'Commune',
        'Point_Vaccination', 'Latitude', 'Longitude', 'Population_Approx',
        'Enfants_Age_Vaccination', 'Enfants_Zero_Dose', 'Source_Energie',
        'Calendrier_Vaccinal', 'Indicateurs_Connus', 'Defis_Principaux',
        'Propositions_Solutions'
    ]
    # Assurez-vous que seules les colonnes existantes sont sélectionnées pour éviter les erreurs
    final_export_df = filtered_df[[col for col in export_cols if col in filtered_df.columns]].copy()

    # Utiliser dcc.send_data_frame pour générer et télécharger le fichier Excel
    return dcc.send_data_frame(
        final_export_df.to_excel,
        filename="rapport_vaccination.xlsx",
        sheet_name="Données Vaccination",
        index=False
    )


# --- Callback pour l'export PDF ---
@app.callback(
    Output("download-pdf-report", "data"),
    Input("btn-export-pdf", "n_clicks"),
    [
        Input('dropdown-wilaya', 'value'),
        Input('dropdown-commune', 'value'),
        Input('dropdown-source-energie', 'value'),
    ],
    prevent_initial_call=True,
)
def export_pdf_report(n_clicks, selected_wilayas, selected_communes, selected_sources_energie):
    if n_clicks is None:
        return None

    # --- 1. Recréer le DataFrame filtré ---
    filtered_df = df_global.copy()
    if selected_wilayas and len(selected_wilayas) > 0:
        filtered_df = filtered_df[filtered_df['Wilaya'].isin(selected_wilayas)]
    if selected_communes and len(selected_communes) > 0:
        filtered_df = filtered_df[filtered_df['Commune'].isin(selected_communes)]
    if selected_sources_energie and len(selected_sources_energie) > 0:
        filtered_df = filtered_df[filtered_df['Source_Energie'].isin(selected_sources_energie)]

    # --- 2. Générer et exporter les figures en images base64 ---
    # Génération et exportation du graphique "Enfants Zéro Dose par Commune"
    enfants_zero_dose_chart_fig_b64 = ""
    if 'Commune' in filtered_df.columns and 'Enfants_Zero_Dose' in filtered_df.columns and not filtered_df.empty:
        enfants_zero_dose_commune = filtered_df.groupby('Commune')['Enfants_Zero_Dose'].sum().sort_values(ascending=False).head(10)
        enfants_zero_dose_chart_fig = px.bar(
            enfants_zero_dose_commune,
            x=enfants_zero_dose_commune.index,
            y='Enfants_Zero_Dose',
            title="Top 10 Enfants Zéro Dose par Commune",
            labels={'x': 'Commune', 'y': 'Nombre d\'enfants Zéro Dose'},
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        try:
            img_bytes = enfants_zero_dose_chart_fig.to_image(format="png", engine="kaleido", width=800, height=400, scale=2)
            enfants_zero_dose_chart_fig_b64 = base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            print(f"Erreur lors de l'exportation du graphique Enfants Zéro Dose: {e}")
            enfants_zero_dose_chart_fig_b64 = "" # Assurez-vous qu'il est vide en cas d'erreur
            
    # Génération et exportation de la "Carte des Points de Vaccination"
    map_fig_b64 = ""
    if 'Latitude' in filtered_df.columns and 'Longitude' in filtered_df.columns and not filtered_df.empty:
        map_fig = px.scatter_map(
            filtered_df,
            lat="Latitude",
            lon="Longitude",
            hover_name="Point_Vaccination",
            hover_data={
                "Commune": True,
                "Wilaya": True,
                "Enfants_Zero_Dose": True,
                "Latitude": False,
                "Longitude": False
            },
            color="Wilaya",
            size="Enfants_Zero_Dose",
            zoom=6,
            height=400,
            title="Carte des Points de Vaccination" # Titre à utiliser pour le PDF
        )
        map_fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
        try:
            img_bytes_map = map_fig.to_image(format="png", engine="kaleido", width=800, height=400, scale=2)
            map_fig_b64 = base64.b64encode(img_bytes_map).decode("utf-8")
        except Exception as e:
            print(f"Erreur lors de l'exportation de la carte: {e}")
            map_fig_b64 = "" # Assurez-vous qu'il est vide en cas d'erreur


    # --- 3. Préparer le tableau de données pour l'HTML ---
    display_cols = ['ID_Formulaire', 'Responsable', 'Wilaya', 'Commune', 'Point_Vaccination',
                    'Enfants_Zero_Dose', 'Defis_Principaux', 'Propositions_Solutions'] # Colonnes à afficher dans le PDF
    existing_display_cols = [col for col in display_cols if col in filtered_df.columns]
    
    table_html = filtered_df[existing_display_cols].to_html(index=False, classes='table table-striped table-bordered')

    # --- 4. Construire le contenu HTML du rapport ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Rapport de Vaccination</title>
        <style>
            body {{ font-family: sans-serif; margin: 20mm; }}
            h1 {{ text-align: center; color: #333; }}
            h2 {{ color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .kpi-section {{ text-align: center; margin-bottom: 20px; }}
            .kpi {{ display: inline-block; margin: 0 15px; padding: 10px 20px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            img {{ max-width: 100%; height: auto; display: block; margin: 20px auto; }}
        </style>
    </head>
    <body>
        <h1>Rapport de l'Enquête de Vaccination</h1>
        <p>Ce rapport présente les données filtrées au moment de l'exportation.</p>

        <h2>Indicateurs Clés</h2>
        <div class="kpi-section">
            <div class="kpi">Points de Vaccination: {filtered_df['Point_Vaccination'].nunique() if 'Point_Vaccination' in filtered_df.columns and not filtered_df.empty else 0}</div>
            <div class="kpi">Enfants Zéro Dose: {filtered_df['Enfants_Zero_Dose'].sum() if 'Enfants_Zero_Dose' in filtered_df.columns and not filtered_df.empty else 0}</div>
        </div>

        <h2>Carte des Points de Vaccination</h2>
        {"<img src='data:image/png;base64," + map_fig_b64 + "' alt='Carte des Points de Vaccination'>" if map_fig_b64 else "<p>Données de carte non disponibles.</p>"}

        <h2>Graphique: Enfants Zéro Dose par Commune</h2>
        {"<img src='data:image/png;base64," + enfants_zero_dose_chart_fig_b64 + "' alt='Enfants Zéro Dose par Commune'>" if enfants_zero_dose_chart_fig_b64 else "<p>Données de graphique non disponibles.</p>"}

        <h2>Données Détaillées</h2>
        {table_html if not filtered_df.empty and existing_display_cols else "<p>Aucune donnée disponible pour le tableau avec la sélection actuelle.</p>"}

    </body>
    </html>
    """

    # --- 5. Génération du PDF avec WeasyPrint ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        HTML(string=html_content).write_pdf(tmp_pdf.name, stylesheets=[CSS(string='''
            @page { size: A4; margin: 1in; }
            table { page-break-inside: auto; }
            tr { page-break-inside: avoid; page-break-after: auto; }
            thead { display: table-header-group; }
        ''')])
        pdf_path = tmp_pdf.name

    # --- 6. Téléchargement du PDF ---
    return dcc.send_file(pdf_path, filename="rapport_vaccination.pdf")


# --- Exécution de l'application ---

if __name__ == '__main__':
    app.run(debug=True)



