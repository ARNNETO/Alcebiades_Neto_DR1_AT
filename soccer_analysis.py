import streamlit as st
from statsbombpy import sb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import Pitch
import io

# Cache para otimizar o carregamento de dados grandes
@st.cache_data
def load_competitions():
    return sb.competitions()

@st.cache_data
def load_matches(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)

@st.cache_data
def load_events(match_id):
    return sb.events(match_id=match_id)

def main():
    # Inicializando Session State se ainda não existir
    if 'competition' not in st.session_state:
        st.session_state['competition'] = None
    if 'season' not in st.session_state:
        st.session_state['season'] = None
    if 'match' not in st.session_state:
        st.session_state['match'] = None
    if 'selected_player' not in st.session_state:
        st.session_state['selected_player'] = None

    # Sidebar para selecionar o menu
    st.sidebar.header("Navegação")
    menu = ['Home', 'Análise de Campeonato']
    choice = st.sidebar.selectbox('Menu', menu)

    if choice == 'Home':
        st.title('Plataforma de Análise de Futebol')
        st.subheader('Seja bem-vindo à sua plataforma de análise de futebol.')
        st.write("""
            Nesta plataforma, você pode explorar competições, partidas e realizar análises detalhadas sobre jogadores.
        """)
    elif choice == 'Análise de Campeonato':
        st.title('Análise de Campeonato')

        # Container para toda a análise
        with st.container():
            # Colunas para selecionar Competição e Temporada
            st.subheader('Selecione Competição e Temporada')

            col1, col2 = st.columns(2)

            with col1:
                # Seleção de Competição 
                competitions = load_competitions()
                competition_name = competitions['competition_name'].unique()
                selected_competition = st.selectbox(
                    'Selecione uma competição', competition_name, key='competition')

            with col2:
                # Filtra a competição selecionada e selecionar a temporada
                competition_filtered = competitions[competitions['competition_name'] == selected_competition]
                season_name = competition_filtered['season_name'].unique()
                selected_season = st.selectbox(
                    'Selecione uma temporada', season_name, key='season')

            # Verificase o filtro retornou dados
            if competition_filtered.empty:
                st.error('Nenhuma competição encontrada para os parâmetros selecionados.')
                return

            # Verificase há temporada correspondente
            if competition_filtered[competition_filtered['season_name'] == selected_season].empty:
                st.error('Nenhuma temporada encontrada para os parâmetros selecionados.')
                return

            # Obter IDs da competição e temporada
            competition_row = competition_filtered[competition_filtered['season_name'] == selected_season]
            competition_id = competition_row['competition_id'].values[0] if len(competition_row) > 0 else None
            season_id = competition_row['season_id'].values[0] if len(competition_row) > 0 else None

            if competition_id is None or season_id is None:
                st.error("Erro ao recuperar IDs de competição ou temporada.")
                return

            # Seleciona partida
            matches = load_matches(competition_id, season_id)
            if matches.empty:
                st.error('Nenhuma partida encontrada para os parâmetros selecionados.')
                return

            matches['match_info'] = matches['home_team'] + " vs " + matches['away_team']
            selected_match = st.selectbox('Selecione uma partida', matches['match_info'], key='match')

            # Exibeinformações da partida
            match_data = matches[matches['match_info'] == selected_match]

            if match_data.empty:
                st.error('Nenhuma informação da partida encontrada.')
                return

            with st.spinner('Carregando dados da partida...'):
                events = load_events(match_data['match_id'].values[0])
                if events.empty:
                    st.error('Nenhum evento encontrado para esta partida.')
                    return

            # Tabs para dividir as informações
            tabs = st.tabs(["Detalhes da Partida", "Análise de Jogador", "Gráficos da Partida", "Configurações Avançadas"])

            with tabs[0]:
                st.subheader('Detalhes da Partida')
                st.write(f"Data: {match_data['match_date'].values[0]}")
                st.write(f"Estádio: {match_data['stadium'].values[0]}")
                st.write(f"Time da Casa: {match_data['home_team'].values[0]}")
                st.write(f"Time Visitante: {match_data['away_team'].values[0]}")
                st.write(f"Placar Final: {match_data['home_score'].values[0]} - {match_data['away_score'].values[0]}")

                # Estatísticas da partida
                st.subheader('Estatísticas da Partida')

                # Total de gols na partida
                total_goals = events[events['type'] == 'Shot']['shot_outcome'].value_counts().get('Goal', 0)
                
                # Total de passes completados
                successful_passes = len(events[(events['type'] == 'Pass') & (events['pass_outcome'].isna())])
                
                # Total de chutes e taxa de conversão de chutes em gol
                total_shots = len(events[events['type'] == 'Shot'])
                conversion_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

                # Exibe os indicadores
                col1, col2, col3 = st.columns(3)

                col1.metric("Total de Gols", total_goals)
                col2.metric("Passes Completos", successful_passes)
                col3.metric("Taxa de Conversão de Chutes", f"{conversion_rate:.2f}%", delta=f"{conversion_rate:.2f}%")

                # Seleção do intervalo de tempo da partida
                st.subheader("Filtrar eventos por intervalo de tempo")
                min_time, max_time = st.slider('Selecione o intervalo de tempo da partida (em minutos)', 0, 90, (0, 90))
                filtered_by_time = events[events['minute'].between(min_time, max_time)]

                # Mostra eventos filtrados
                st.write(f"Eventos entre {min_time} e {max_time} minutos:")
                st.dataframe(filtered_by_time[['minute', 'type', 'player', 'team']].dropna())

                # Botão para baixar os dados
                st.download_button(
                    label="Baixar dados filtrados como CSV",
                    data=filtered_by_time.to_csv(index=False).encode('utf-8'),
                    file_name=f'dados_filtrados_partida_{min_time}-{max_time}.csv',
                    mime='text/csv',
                )

            with tabs[1]:
                st.subheader('Análise de Jogador')

                # Seleciona de jogador
                players = events['player'].dropna().unique()
                selected_player = st.selectbox('Selecione um jogador', players, key='selected_player')

                # Filtra eventos relacionados ao jogador selecionado
                if st.button('Filtrar eventos do jogador'):
                    player_events = events[events['player'] == selected_player]
                    st.write(f"Total de eventos para {selected_player}: {len(player_events)}")
                    st.write(player_events[['minute', 'type', 'location']].head())

                    # Botão para baixar os dados dos eventos do jogador filtrado
                    st.download_button(
                        label=f"Baixar eventos de {selected_player} como CSV",
                        data=player_events.to_csv(index=False).encode('utf-8'),
                        file_name=f'eventos_{selected_player}.csv',
                        mime='text/csv',
                    )

            with tabs[2]:
                st.subheader('Visualizações Estatísticas')

                # Mapa de passes
                st.subheader('Mapa de Passes')
                pitch = Pitch(line_color='black', pitch_color='#aabb97')
                fig, ax = pitch.draw(figsize=(10, 6))

                passes = events[(events['type'] == 'Pass') & (events['pass_outcome'].isna())]

                pitch.arrows(passes['location'].apply(lambda x: x[0]), passes['location'].apply(lambda x: x[1]),
                             passes['pass_end_location'].apply(lambda x: x[0]), passes['pass_end_location'].apply(lambda x: x[1]),
                             ax=ax, width=2, headwidth=3, color='blue', label='Passes Completos')

                ax.legend()
                st.pyplot(fig)

                # Mapa de chutes
                st.subheader('Mapa de Chutes')
                fig, ax = pitch.draw(figsize=(10, 6))

                shots = events[events['type'] == 'Shot']

                pitch.scatter(shots['location'].apply(lambda x: x[0]), shots['location'].apply(lambda x: x[1]),
                              c=shots['shot_outcome'].apply(lambda x: 'red' if x == 'Goal' else 'blue'), ax=ax, s=100)

                st.pyplot(fig)

                # Exibe gráfico do Seaborn
                st.subheader('Relação entre Chutes e Gols')
                fig, ax = plt.subplots()
                sns.scatterplot(data=shots, x='minute', y='type', hue='shot_outcome', ax=ax)
                ax.set_xlabel('Minuto')
                ax.set_ylabel('Chute')
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles, labels, title="Resultado Dos Chutes")
                st.pyplot(fig)

            with tabs[3]:
                st.subheader('Configurações Avançadas')

                # Seleciona número de eventos para exibir
                event_count = st.number_input('Quantidade de eventos a serem exibidos', min_value=5, max_value=100, value=10)
                selected_events = events.head(event_count)
                st.dataframe(selected_events[['minute', 'type', 'player', 'team']])

                # Comparação entre dois jogadores
                st.subheader('Comparação entre dois jogadores')
                player_1 = st.selectbox('Jogador 1', players, key='player1')
                player_2 = st.selectbox('Jogador 2', players, key='player2')

                if st.button('Comparar Jogadores'):
                    events_player_1 = events[events['player'] == player_1]
                    events_player_2 = events[events['player'] == player_2]
                    
                    st.write(f"Eventos de {player_1}:")
                    st.dataframe(events_player_1[['minute', 'type', 'location']].head())
                    
                    st.write(f"Eventos de {player_2}:")
                    st.dataframe(events_player_2[['minute', 'type', 'location']].head())

                    # Comparação visual: por exemplo, número de passes bem-sucedidos
                    st.metric(f"Passes Completos ({player_1})", len(events_player_1[events_player_1['type'] == 'Pass']))
                    st.metric(f"Passes Completos ({player_2})", len(events_player_2[events_player_2['type'] == 'Pass']))

if __name__ == '__main__':
    main()
