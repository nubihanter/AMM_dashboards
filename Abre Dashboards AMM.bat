@echo off
title Rodar Dashboards Streamlit

echo Iniciando servidores...
echo.

:: Dashboard de Estoque
:: Link: http://localhost:8501
start "Streamlit Estoque" python -m streamlit run "C:\Users\User\AMM_data_management\dashboardEstoque.py" --server.port 8501

:: Dashboard de Vendas
:: Link: http://localhost:8502
start "Streamlit Vendas" python -m streamlit run "C:\Users\User\AMM_data_management\dashboardVendas_vendedor.py" --server.port 8502

:: Dashboard Gerencial
:: Link: http://localhost:8503
start "Streamlit Gerencial" python -m streamlit run "C:\Users\User\AMM_data_management\dashboardVendas_gerencial.py" --server.port 8503

echo --------------------------------------------------
echo Servidores iniciados com sucesso!
echo.
echo Dashboard ESTOQUE: http://localhost:8501
echo Dashboard VENDAS:  http://localhost:8502
echo Dashboard GERENCIAL: http://localhost:8503
echo --------------------------------------------------
echo.
pause