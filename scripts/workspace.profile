#! /bin/bash

WS_HELP="

  ${BLUE}Bienvenido a El-Bisne-Backend workspace${NC}
  =======================================
  
  Funciones diponibles:
  - ${GREEN}comp${NC}: Ejecuta docker-compose
  - ${GREEN}edb${NC}: Ejecuta psql para conectarse a la base de datos
  
"

function edb {
    source .env && psql "${DATABASE_URL/"+asyncpg"/}"
}

function comp {
    sudo docker compose $@ || sudo docker-compose $@
}

function wshelp {
  printf "$WS_HELP"
}

wshelp
