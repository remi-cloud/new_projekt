import type { AboutDetailBundle } from './types'

export const aboutDetailEs: AboutDetailBundle = {
  back: '← Volver a Sobre nosotros',
  learnMore: 'Cómo funciona →',
  notFound: 'Página de metodología no encontrada.',
  howItWorks: 'Cómo funciona',
  topics: {
    'cycles-not-headlines': {
      eyebrow: 'Metodología · Ciclos',
      title: 'Ciclos, no titulares',
      intro:
        'Las señales en Cyclical Academy no se construyen reaccionando a una sola noticia. Se basan en fases de mercado repetibles que históricamente regresaron en escalas de tiempo similares.',
      sections: [
        {
          title: 'Ciclo Bitcoin (364 / 1064 días)',
          body:
            'Tras el ATH, BTC suele entrar en fase bajista (~364 días), luego acumulación y ola alcista (~1064 días). El escáner rastrea días desde ATH, fase (bear / accumulation / bull / distribution) y progreso de fase % — filtro de contexto para cripto y activos correlacionados.',
        },
        {
          title: 'Ciclo presidencial de EE. UU.',
          body:
            'Estadísticamente, el año 3 del mandato tiende a ser el más fuerte para el S&P 500, el año 2 (midterms) el más débil. La plataforma mapea el año de mandato actual y el sesgo histórico — no como garantía, sino como contexto macro para activos de la región US.',
        },
        {
          title: 'Momentum RSI y mapas regionales',
          body:
            'RSI de 14 periodos señala sobreventa (<30) y sobrecompra (>70) en contexto de ciclo. Valoraciones separadas para USA, Europa, Asia, Polonia, EM — para que la señal de un instrumento no ignore su entorno macro.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Pestaña Ciclos (tarjetas BTC y presidenciales), Dashboard global, valoraciones en Mercados y Oportunidades.',
    },
    'own-schemas': {
      eyebrow: 'Metodología · Modelos',
      title: 'Marcos propietarios',
      intro:
        'Los modelos KAR Digital combinan capas que normalmente se analizan por separado: precio, ciclo, momentum y macro regional en una valoración de instrumento.',
      sections: [
        {
          title: 'Capas de evaluación',
          body:
            'Cada instrumento pasa por contexto de precio 52 semanas, alineación ciclo BTC (cripto) o ciclo presidencial (US), momentum RSI y mapa regional. Resultado: Comprar, Vender, Mantener u Observar.',
        },
        {
          title: 'Confianza de señal (%)',
          body:
            'El porcentaje en la etiqueta (p. ej. 80,5 %) es acuerdo entre capas — mayor significa mejor alineación ciclo/precio/momentum. 80 %+ es oportunidad fuerte en nuestro marco; por debajo de 60 % requiere cautela.',
        },
        {
          title: 'Calibración plurianual',
          body:
            'Los modelos no se ajustan a la «tendencia de la semana». Parámetros de fase BTC, umbrales RSI y pesos regionales provienen de años de observación — el paper trading verifica disciplina de ejecución, no persecución del gráfico.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Oportunidades (tarjetas con %), detalle de instrumento, guía de confianza en Dashboard, análisis del Agente IA.',
    },
    'long-term-horizon': {
      eyebrow: 'Metodología · Horizonte',
      title: 'Horizonte a largo plazo',
      intro:
        'La construcción de capital se mide en años, no en minutos. La plataforma apoya la asignación y la paciencia — no el sobreoperar.',
      sections: [
        {
          title: 'Marcadores entrada / salida (WEJ / WYJ)',
          body:
            'Los marcadores en el gráfico muestran zonas sugeridas de entrada (WEJ) y salida (WYJ) según fases de ciclo y momentum — marcos educativos para su propia evaluación, no órdenes automáticas.',
        },
        {
          title: 'Paper trading sin presión',
          body:
            'Cartera virtual de 1.000.000 PLN, órdenes limit/stop/TP y archivo de posiciones cerradas permiten practicar sin riesgo de capital real.',
        },
        {
          title: 'Mentalidad de asignación',
          body:
            '«Observar» o «Mantener» es tan importante como «Comprar» — a menudo la mejor decisión es esperar una mejor fase del ciclo. El horizonte largo reduce reacciones emocionales a titulares.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Cartera (paper), gráfico del instrumento con marcadores WEJ/WYJ, Oportunidades filtradas por fuerza de señal.',
    },
    'terminal-not-tabloid': {
      eyebrow: 'Metodología · Filosofía',
      title: 'Terminal, no tabloide',
      intro:
        'Cyclical Academy es una herramienta analítica estilo mission control — gráficos, datos, ciclos y valoraciones. Sin clickbait ni promesas de ganancias rápidas.',
      sections: [
        {
          title: 'Gráficos y datos en vivo',
          body:
            'TradingView, presets 1M–5Y, RSI, precios en vivo e historial de velas por instrumento. Las noticias macro son una capa de contexto separada, no el núcleo de la señal.',
        },
        {
          title: 'Metodología transparente',
          body:
            'Cada tarjeta de ciclo u oportunidad muestra la justificación — de dónde viene la señal. Sin caja negra; el usuario puede verificar fase y parámetros.',
        },
        {
          title: 'Educación, no asesoramiento',
          body:
            'El contenido es para aprendizaje y autoanálisis. El Agente IA responde solo preguntas financieras y cierra con un disclaimer educativo.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Mercados → instrumento, Dashboard, Agente IA (/agent), subpáginas Sobre nosotros.',
    },
    'not-breaking-news': {
      eyebrow: 'Filosofía · Límites',
      title: 'No somos una plataforma de breaking news',
      intro:
        'Las noticias macro (Fed, CPI, geopolítica) son contexto importante — pero no generan señales de compra/venta automáticas cada minuto.',
      sections: [
        {
          title: 'Economía de eventos vs ciclos',
          body:
            'La mayoría de medios financieros viven de eventos puntuales. Los tratamos como contexto (pestaña News, calendario macro) mientras el núcleo de valoración es la repetibilidad de fases y la estructura del mercado.',
        },
        {
          title: 'RSS y calendario como contexto',
          body:
            'Las noticias se actualizan cada 2 minutos; el calendario muestra FOMC, CPI, NFP — las alertas push se centran en eventos macro significativos, no en cada titular. Las señales de trading siguen viniendo del escáner cíclico.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Pestaña News (contexto) vs Oportunidades / Ciclos (señales estructurales).',
    },
    'not-headline-trading': {
      eyebrow: 'Filosofía · Límites',
      title: 'No operamos según titulares',
      intro:
        'Las decisiones en nuestro marco provienen de patrones que construimos y probamos con datos históricos y paper trading.',
      sections: [
        {
          title: 'Patrón antes que impulso',
          body:
            'Las reacciones a titulares suelen ser tardías y emocionales. El esquema cíclico pregunta: en qué fase estamos, ¿confirma el momentum?, ¿apoya el macro regional? — antes de pulsar Comprar.',
        },
        {
          title: 'Pruebas en paper',
          body:
            'Los cambios de lógica deben pasar por la cartera simulada: limit, stop, take profit y archivo de P/L cerrado — sin verificación en cuenta live.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Cartera paper, historial por instrumento, justificación en cada oportunidad.',
    },
    'not-minute-signals': {
      eyebrow: 'Filosofía · Límites',
      title: 'No prometemos señales cada minuto',
      intro:
        'Los escaneos completos corren cada pocos minutos, pero la calidad de señal supera la cantidad. Ofrecemos un marco más sereno para inversores a largo plazo.',
      sections: [
        {
          title: 'Frecuencia de escaneo',
          body:
            'Análisis completo (52 sem., señales, ciclos) — cada 5 min en segundo plano. Actualización de precios — cada minuto. No es un terminal de scalping; las señales se refieren a fases de semanas y meses.',
        },
        {
          title: 'Calidad > cantidad',
          body:
            'Oportunidades lista instrumentos con mayor acuerdo entre capas. Un filtro vacío es información — a veces la mejor señal es no operar.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Oportunidades, estado del escáner en Dashboard, botón «Escanear mercados».',
    },
    'method-map-cycles': {
      eyebrow: 'Método · Paso 1',
      title: 'Mapeamos ciclos',
      intro:
        'Primer paso: entender la fase de ciclo global y regional — desde BTC hasta el ritmo presidencial US y mapas macro.',
      sections: [
        {
          title: 'Bitcoin como reloj cripto',
          body:
            'Días desde ATH, fase bear/bull, días restantes — en la tarjeta Ciclo Bitcoin. Sesga señales para BTC, ETH y ETF cripto.',
        },
        {
          title: 'Mandato US y regiones',
          body:
            'Ciclo presidencial para activos US; instantáneas regionales (UE, Asia, PL, EM) con valoración macro e instrumentos representativos.',
        },
        {
          title: 'El escáner lo combina todo',
          body:
            'En escaneo completo, cada activo monitorizado recibe valoración con el ciclo adecuado para su clase de activo y región.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Ciclos, Dashboard (resumen BTC + regional), tarjetas de inicio.',
    },
    'method-layers': {
      eyebrow: 'Método · Paso 2',
      title: 'Combinamos capas',
      intro:
        'Un indicador rara vez basta. Fusionamos precio, momentum, macro y WEJ/WYJ en una valoración con confianza %.',
      sections: [
        {
          title: 'Capa de precio',
          body:
            'Posición vs rango 52 semanas, fase (bear, accumulation, bull, distribution) y tendencia estructural en el gráfico.',
        },
        {
          title: 'Capa de momentum',
          body:
            'RSI 14 — zonas de sobreventa/sobrecompra interpretadas en contexto de fase de ciclo, no como compra/venta automática.',
        },
        {
          title: 'Síntesis del escáner',
          body:
            'El analizador de activos agrega capas en SignalAction + confianza + justificación en tarjetas de oportunidad y tablas de mercados.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Oportunidades, Mercados, detalle de instrumento, Agente IA → «Análisis completo».',
    },
    'method-discipline': {
      eyebrow: 'Método · Paso 3',
      title: 'Probamos la disciplina',
      intro:
        'El paper trading con limit, stop y take profit es campo de entrenamiento — sin arriesgar capital real al inicio.',
      sections: [
        {
          title: 'Cartera 1.000.000 PLN',
          body:
            'Efectivo inicial en PLN, conversiones USD/EUR, precios en vivo y P/L abierto/realizado. El reset de cartera permite reiniciar pruebas.',
        },
        {
          title: 'Órdenes avanzadas',
          body:
            'Market, limit, stop y TP — cancelar una o todas las órdenes por símbolo. Cierre parcial (p. ej. 50 %).',
        },
        {
          title: 'Archivo y aprendizaje',
          body:
            'Posiciones cerradas con fecha y P/L enseñan si la ejecución coincidió con la señal cíclica — sin presión de cuenta broker.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Cartera, trading en página de instrumento, posiciones abiertas y cerradas.',
    },
    'method-years': {
      eyebrow: 'Método · Paso 4',
      title: 'Pensamos en años',
      intro:
        'Las señales sirven la asignación de capital durante muchos años — los ciclos BTC y presidenciales duran más que una sesión de trading.',
      sections: [
        {
          title: 'La paciencia como ventaja',
          body:
            'La acumulación post-bear puede durar meses. Una señal «Observar» en distribución protege contra entradas tardías en burbuja.',
        },
        {
          title: 'Rebalancear, no entrar en pánico',
          body:
            'La valoración global (cuántos instrumentos en Comprar/Vender) muestra el panorama — risk-on vs risk-off — en lugar de reaccionar a una vela.',
        },
      ],
      inAppTitle: 'Dónde verlo',
      inAppBody: 'Dashboard (valoración global), Ciclos (progreso de fase %), presets largos de gráfico 1A/5A.',
    },
  },
}
