// Prueba B3: ARX (librería libarx 3.9.2) anonimiza el registro «persona» de Pagila con k-anonimato.
//
// Lo llama b3_arx.py (paso `anonimizar`) dentro de un contenedor eclipse-temurin:21-jdk:
//   java -cp libarx-3.9.2.jar:. ArxB3 <dir_entrada> <dir_salida> <variante> <k> <supresion> [cuasi,...]
// El último argumento (opcional) elige qué cuasi-identificadores se generalizan; los de CUASI que no
// estén en la lista pasan a ser identificadores (se tapan con '*').
// Entrada: <dir_entrada>/persona.csv y <dir_entrada>/jerarquia_<columna>.csv (separador ';').
// Salida:  <dir_salida>/<variante>.csv (la tabla anonimizada) y <variante>_metricas.json.
import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

import org.deidentifier.arx.ARXAnonymizer;
import org.deidentifier.arx.ARXConfiguration;
import org.deidentifier.arx.ARXLattice.ARXNode;
import org.deidentifier.arx.ARXResult;
import org.deidentifier.arx.AttributeType;
import org.deidentifier.arx.AttributeType.Hierarchy;
import org.deidentifier.arx.Data;
import org.deidentifier.arx.DataDefinition;
import org.deidentifier.arx.DataHandle;
import org.deidentifier.arx.aggregates.StatisticsEquivalenceClasses;
import org.deidentifier.arx.criteria.KAnonymity;
import org.deidentifier.arx.risk.RiskModelSampleRisks;

public class ArxB3 {

    // Identificadores directos: ARX los reemplaza por '*'.
    static final String[] IDENTIFICADORES = {"first_name", "last_name", "email", "address", "phone"};
    // Cuasi-identificadores: se generalizan según su jerarquía.
    static final String[] CUASI = {"district", "postal_code", "city", "country", "create_date"};
    // El resto queda igual. Hay que declararlo: ARX trata como identificador (y borra) toda columna
    // sin tipo, incluida la clave customer_id, sin la cual no se puede volver a la base.
    static final String[] INSENSIBLES = {"customer_id", "store_id", "activebool", "active"};

    public static void main(String[] args) throws Exception {
        File entrada = new File(args[0]), salida = new File(args[1]);
        String variante = args[2];
        int k = Integer.parseInt(args[3]);
        double supresion = Double.parseDouble(args[4]);
        salida.mkdirs();

        Data data = Data.create(new File(entrada, "persona.csv"), StandardCharsets.UTF_8, ';');
        DataDefinition def = data.getDefinition();
        for (String c : IDENTIFICADORES) def.setAttributeType(c, AttributeType.IDENTIFYING_ATTRIBUTE);
        for (String c : INSENSIBLES) def.setAttributeType(c, AttributeType.INSENSITIVE_ATTRIBUTE);
        java.util.List<String> elegidos = args.length > 5 ? java.util.Arrays.asList(args[5].split(","))
                                                          : java.util.Arrays.asList(CUASI);
        for (String c : CUASI) {
            if (!elegidos.contains(c)) {
                def.setAttributeType(c, AttributeType.IDENTIFYING_ATTRIBUTE);
                continue;
            }
            Hierarchy h = Hierarchy.create(new File(entrada, "jerarquia_" + c + ".csv"), StandardCharsets.UTF_8, ';');
            def.setAttributeType(c, h);
        }

        ARXConfiguration cfg = ARXConfiguration.create();
        cfg.addPrivacyModel(new KAnonymity(k));
        cfg.setSuppressionLimit(supresion);

        Map<String, Object> m = new LinkedHashMap<>();
        m.put("variante", variante);
        m.put("arx", ARXAnonymizer.VERSION);
        m.put("k", k);
        m.put("limite_supresion", supresion);
        m.put("cuasi_identificadores", elegidos);
        m.put("modelo_calidad", cfg.getQualityModel().getName());
        m.put("filas", data.getHandle().getNumRows());
        m.put("riesgo_antes", riesgos(data.getHandle()));

        ARXAnonymizer anon = new ARXAnonymizer();
        long t0 = System.nanoTime();
        ARXResult res = anon.anonymize(data, cfg);
        m.put("segundos_anonimizar", (System.nanoTime() - t0) / 1e9);
        m.put("solucion_encontrada", res.isResultAvailable());
        m.put("optimo_global", res.getOptimumFound());

        if (res.isResultAvailable()) {
            ARXNode opt = res.getGlobalOptimum();
            Map<String, Integer> niveles = new LinkedHashMap<>();
            String[] qis = opt.getQuasiIdentifyingAttributes();
            int[] t = opt.getTransformation();
            for (int i = 0; i < qis.length; i++) niveles.put(qis[i], t[i]);
            m.put("nivel_por_cuasi_identificador", niveles);
            m.put("perdida_informacion", opt.getHighestScore().toString());

            DataHandle out = res.getOutput(false);
            StatisticsEquivalenceClasses ec = out.getStatistics().getEquivalenceClassStatistics();
            m.put("filas_suprimidas", ec.getNumberOfSuppressedRecords());
            m.put("clases_equivalencia", ec.getNumberOfEquivalenceClasses());
            m.put("clase_min", ec.getMinimalEquivalenceClassSize());
            m.put("clase_promedio", ec.getAverageEquivalenceClassSize());
            m.put("clase_max", ec.getMaximalEquivalenceClassSize());
            m.put("riesgo_despues", riesgos(out));
            out.save(new File(salida, variante + ".csv"), ';');
        }
        try (PrintWriter w = new PrintWriter(new File(salida, variante + "_metricas.json"), "UTF-8")) {
            w.println(json(m));
        }
        System.out.println(json(m));
    }

    // Riesgo de reidentificación según el modelo del fiscal (prosecutor): el atacante sabe que la
    // persona está en los datos. Riesgo de una fila = 1 / tamaño de su clase de equivalencia.
    static Map<String, Object> riesgos(DataHandle h) {
        RiskModelSampleRisks r = h.getRiskEstimator().getSampleBasedReidentificationRisk();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("riesgo_maximo", r.getHighestRisk());
        m.put("riesgo_promedio", r.getAverageRisk());
        m.put("filas_con_riesgo_maximo", r.getNumRecordsAffectedByHighestRisk());
        m.put("fraccion_con_riesgo_maximo", r.getFractionOfRecordsAffectedByHighestRisk());
        return m;
    }

    static String json(Object o) {
        if (o instanceof Map<?, ?> map) {
            StringBuilder b = new StringBuilder("{");
            boolean primero = true;
            for (Map.Entry<?, ?> e : map.entrySet()) {
                if (!primero) b.append(", ");
                primero = false;
                b.append('"').append(e.getKey()).append("\": ").append(json(e.getValue()));
            }
            return b.append('}').toString();
        }
        if (o instanceof Number || o instanceof Boolean) return o.toString();
        return '"' + String.valueOf(o).replace("\\", "\\\\").replace("\"", "\\\"") + '"';
    }
}
