# Analisis red vial de Costa Rica
# Autor: ernestochaveschaves@gmail.com
# Fecha de creación: 04/03/2022


import math

import streamlit as st

import pandas as pd
import geopandas as gpd

import plotly.express as px

import folium
from folium import Marker
from folium.plugins import MarkerCluster
from folium.plugins import HeatMap
from streamlit_folium import folium_static

#
# Configuración de la página
#
st.set_page_config(layout='wide')


#
# TÍTULO Y DESCRIPCIÓN DE LA APLICACIÓN
#

st.title('Análisis red vial de Costa Rica')
st.markdown('Esta aplicación presenta visualizaciones tabulares, gráficas y geoespaciales de datos de viales de los cantones de Costa Rica')
st.markdown('El usuario debe seleccionar la categoria de la via que a su vez se usara para filtrar las visualizaciones')
st.markdown('La aplicación mostrará un conjunto de tablas, gráficos y mapas correspondientes a la densidad y longitud de las vias por cantón.')
st.markdown('El repositorio se puede encontrar en https://github.com/ernestochaves/analisisredvial.')
#
# ENTRADAS
#

# Carga de datos
# st.header('Cargamos el geojson que tenemos con la información de la red vial')
pathRedVial = "https://github.com/ernestochaves/analisisredvial/raw/main/datos/redvial.geojson"
pathCantones = "https://github.com/ernestochaves/analisisredvial/raw/main/datos/costarica_cantones.geojson"
#Cargamos ambos en un datafram en pandas
redVialDF = gpd.read_file(pathRedVial)
cantonesDF = gpd.read_file(pathCantones)
# Se continúa con el procesamiento solo si hay un archivo de datos cargado
#if archivo_registros_presencia is not None:

# Especificación de filtros
# st.header('Filtros de datos')
# Categoria de carretera
categorias = redVialDF.categoria.unique().tolist()
categorias.sort()
filtro_categorias = st.sidebar.selectbox('Seleccione la categoria', categorias)

#
# PROCESAMIENTO
#

# Filtrado
redVialDF = redVialDF[redVialDF['categoria'] == filtro_categorias]
# Union de los datos
# queremos guardar la geometria de la linea para calcular la interseccion
redVialDF['tempgeom'] = redVialDF.geometry
# Vamos a tratar de hacer el join usando geopandas
viascantonesjoin = cantonesDF.sjoin(redVialDF, how="left", predicate="intersects")
#Intentando calcular la interseccion entre el canton y cada linea
#Nota: en este caso intento cambiar el crs para evitar este warning 
#UserWarning: Geometry is in a geographic CRS. Results from 'length' are likely incorrect. Use 'GeoSeries.to_crs()' to re-project geometries to a projected CRS before this operation.
viascantonesjoin['interseccion']=viascantonesjoin.geometry.intersection(viascantonesjoin.tempgeom).to_crs(epsg=3035).length/1000

# Definimos una funcion reutilizable para el filtrado y agrupamiento
def filtrarYAgruparLongitudCarretera(dataframeBase, 
                                     datasetJoin, 
                                     categoriaCarretera, 
                                     nombreColumnaLongitud, 
                                     nuevoNombreColumna):
    datasetFiltradoYAgrupado = datasetJoin[datasetJoin.categoria==categoriaCarretera].groupby("cod_canton").interseccion.sum()
    datasetFiltradoYAgrupado = datasetFiltradoYAgrupado.reset_index()
    datasetFiltradoYAgrupado.rename(columns = {nombreColumnaLongitud: nuevoNombreColumna}, inplace = True)
    dataframeBase = datasetFiltradoYAgrupado.join(dataframeBase.set_index('cod_canton'), on='cod_canton', rsuffix='_b', how='right')
    return dataframeBase

#1. Agrupamos por código de cantón la longitud de las lineas. Luego tenemos la longitud total de lineas dentro del canton
longitudTotalPorCanton = viascantonesjoin.groupby("cod_canton").interseccion.sum()
longitudTotalPorCanton = longitudTotalPorCanton.reset_index()
longitudTotalPorCanton.rename(columns = {'interseccion': 'longitud_vias_total'}, inplace = True)
# Agregamos las columnas al dataframe
cantonesAgrupados = longitudTotalPorCanton.join(cantonesDF.set_index('cod_canton'), on='cod_canton', rsuffix='_b', how='right')

# Agregamos y agregamos la columna de acuerdo al filtro de categorias
cantonesAgrupados=filtrarYAgruparLongitudCarretera(cantonesAgrupados, viascantonesjoin, filtro_categorias,"interseccion", filtro_categorias)

# De la misma forma agregamos la densidad
# para esto quiero hacer el group by con una funcion que tome la suma de las intersecciones y la divida entre el tamaño del canton
def calcular_densidad(grupo):
    return grupo['interseccion'].sum() / float(grupo.iloc[0]['area'])

densidadPorCanton = viascantonesjoin.groupby("cod_canton").apply(calcular_densidad)
densidadPorCanton = densidadPorCanton.reset_index(name='densidad')
# Agregamos las columnas al dataframe
cantonesAgrupados = densidadPorCanton.join(cantonesAgrupados.set_index('cod_canton'), on='cod_canton', rsuffix='_b', how='right')


#
# SALIDAS
#

# Tabla de cantones
st.header('Longitud de vias y densidad por canton')
# st.subheader('st.dataframe()')
st.dataframe(cantonesAgrupados[["canton",filtro_categorias, "densidad" ]]\
        .sort_values(by=['densidad'], inplace=False, ascending=False))

# Definición de columnas
col1, col2 = st.columns(2)

with col1:
    # Graficos de longitos de vias
    st.header('Cantones de mayor longitud de la categoria: ' + filtro_categorias)
    # Dataframe filtrado para usar en graficación
    cantMayorLongitudPorTipoRedVial = cantonesAgrupados[["canton", filtro_categorias]].sort_values(by=filtro_categorias, ascending=False).head(15)
    # st.subheader('px.bar()')
    fig = px.bar(cantMayorLongitudPorTipoRedVial, x="canton", y=filtro_categorias)
    st.plotly_chart(fig)

with col2:
    # Graficos de pastel 
    st.header('Porcentaje de red vial de la categoría: ' + filtro_categorias)
    #Aqui lo que hacemos es el porcetaje de los top, y luego ponemos todos los demas en una categoria. 
    cantonesMasLongitud = cantonesAgrupados[["canton", "longitud_vias_total"]]\
    .sort_values(by="longitud_vias_total", ascending=False).iloc[0:15]

    cantonesMenorLongitud = cantonesAgrupados[["canton", "longitud_vias_total"]]\
    .sort_values(by="longitud_vias_total", ascending=False).iloc[15:]
    cantonesMenorLongitud = cantonesMenorLongitud.sum(numeric_only = True).to_frame().T
    cantonesMenorLongitud["canton"]="Otros Cantones"

    cantonesPorcentaje=pd.concat([cantonesMenorLongitud, cantonesMasLongitud])
    # streamlit
    # st.subheader('st.area_chart()')
    # st.area_chart(registros_presencia_grp_mes)
    # plotly
    # st.subheader('px.area()')
    #fig = px.area(registros_presencia_grp_mes, 
    #            labels={'eventDate':'Mes', 'value':'Registros de presencia'})
    #hacemos un grafico de pastel con los primeros 15
    fig = px.pie(cantonesPorcentaje, values='longitud_vias_total', names='canton', title='Porcentaje de la red vial')
    st.plotly_chart(fig)      


# Mapa de registros de presencia
st.header('Mapa de densidad vial y vias')
# st.subheader('st.map()')
# st.map(registros_presencia.rename(columns = {'decimalLongitude':'longitude', 'decimalLatitude':'latitude'}))

# Creación del mapa base
m = folium.Map(location=[9.8, -84], tiles='openstreetmap', zoom_start=8)

folium.Choropleth(
    geo_data=cantonesDF,
    data=cantonesAgrupados,
    columns=['cod_canton', 'densidad'],
    bins=8,
    key_on='feature.properties.cod_canton',
    fill_color='Reds', 
    fill_opacity=0.5, 
    line_opacity=0.4,
    legend_name='Densidad Vial',
    smooth_factor=0).add_to(m)

#Agregar las vias
estiloVias = {'color': 'red','weight': 2}
layer = folium.GeoJson(
    data=redVialDF["geometry"],
    name='redvial', style_function=lambda x:estiloVias).add_to(m) # 1. keep a reference to GeoJSON layer

# Control de capas
folium.LayerControl().add_to(m)

# Despliegue del mapa
folium_static(m)   