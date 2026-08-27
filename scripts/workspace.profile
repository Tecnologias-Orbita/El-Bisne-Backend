#! /bin/bash

WS_HELP="

  ${BLUE}Bienvenido a El-Bisne-Backend workspace${NC}
  =======================================
  
  Funciones diponibles:
  - ${GREEN}comp${NC}: Ejecuta docker-compose
  
"

function comp {
    sudo docker compose $@ || sudo docker-compose $@
}

function wshelp {
  printf "$WS_HELP"
}

wshelp
