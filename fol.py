
import folium
import geopandas as gpd
import osmnx as ox
import streamlit as st
from streamlit_folium import folium_static

st.set_page_config(layout="wide", page_title="Smart City: Индекс комфорта")

st.title("Мониторинг комфорта городской среды")
st.markdown(
    "Интеллектуальная система пространственной оценки комфорта проживания на основе открытых геоданных."
)

# Боковая панель управления
st.sidebar.header("Параметры анализа")
city_name = st.sidebar.text_input("Город или район:", "Казань")
weight_green = st.sidebar.slider(
    "Важность парков и зелёных зон", 0.0, 1.0, 0.6
)
weight_transport = st.sidebar.slider(
    "Важность близости остановок", 0.0, 1.0, 0.4
)


# Универсальная функция загрузки
@st.cache_data(show_spinner=False)
def load_geodata(place):
    try:
        # Настройка osmnx
        ox.settings.use_cache = True
        ox.settings.log_console = False

        # 1. Граница территории
        area = ox.geocode_to_gdf(place)

        # 2. Выгрузка парков и транспорта (проверяем обе версии osmnx)
        tags_parks = {"leisure": ["park", "garden"]}
        tags_transport = {
            "highway": "bus_stop",
            "railway": ["subway_entrance", "station"],
        }

        if hasattr(ox, "features_from_place"):
            parks = ox.features_from_place(place, tags=tags_parks)
            transport = ox.features_from_place(place, tags=tags_transport)
        else:
            parks = ox.geometries_from_place(place, tags=tags_parks)
            transport = ox.geometries_from_place(place, tags=tags_transport)

        return area, parks, transport, None
    except Exception as e:
        return None, None, None, str(e)


with st.spinner("Загрузка картографических данных..."):
    area, parks, transport, err = load_geodata(city_name)

if area is None:
    st.error(f"Не удалось получить данные для «{city_name}».")
    if err:
        st.warning(f"Детали ошибки: {err}")
    st.info(
        "Совет: попробуйте ввести более крупный город, например: «Казань», «Нижний Новгород» или «Moscow»."
    )
else:
    # Центр карты
    center_lat = area.geometry.centroid.y.values[0]
    center_lon = area.geometry.centroid.x.values[0]

    # Создаем карту
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="cartodbpositron",
    )

    # Граница
    folium.GeoJson(
        area,
        name="Граница города",
        style_function=lambda x: {
            "fillColor": "none",
            "color": "#333",
            "weight": 2,
            "dashArray": "5, 5",
        },
    ).add_to(m)

    # Парки (зелёные)
    if parks is not None and not parks.empty:
        folium.GeoJson(
            parks,
            name="Парки",
            style_function=lambda x: {
                "fillColor": "#2ecc71",
                "color": "#27ae60",
                "weight": 1,
                "fillOpacity": 0.6,
            },
            tooltip="Парковая зона",
        ).add_to(m)

    # Остановки (синие точки)
    if transport is not None and not transport.empty:
        for _, row in transport.head(300).iterrows():  # лимит для быстрой отрисовки
            geom = row.geometry
            pt = geom.centroid if geom.geom_type != "Point" else geom
            folium.CircleMarker(
                location=[pt.y, pt.x],
                radius=3,
                color="#2980b9",
                fill=True,
                fill_color="#3498db",
                tooltip="Транспорт",
            ).add_to(m)

    folium.LayerControl().add_to(m)

    # Вывод
    col1, col2 = st.columns([3, 1])

    with col1:
        folium_static(m, width=850, height=520)

    with col2:
        st.subheader("Статистика среды")
        parks_count = len(parks) if (parks is not None and not parks.empty) else 0
        transport_count = (
            len(transport) if (transport is not None and not transport.empty) else 0
        )

        st.metric(label="Зеленых зон", value=parks_count)
        st.metric(label="Транспортных узлов", value=transport_count)

        # Простой расчет индекса
        score = min(
            100,
            int(
                (parks_count * 0.5 * weight_green)
                + (transport_count * 0.1 * weight_transport)
            )
            + 30,
        )
        st.metric(
            label="Индекс комфорта",
            value=f"{score}/100",
            delta="Комфортная зона" if score >= 50 else "Дефицит инфраструктуры",
        )