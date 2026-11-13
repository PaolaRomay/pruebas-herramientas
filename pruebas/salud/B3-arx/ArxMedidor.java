// B3m / B3s: ARX como medidor de riesgo del registro «paciente» (k-anonimato y l-diversidad).
//
// Lo llama b3_arx_salud.py dentro de un contenedor eclipse-temurin:21-jdk:
//   java -cp libarx-3.9.2.jar:. ArxMedidor <dir> <nombre> <k> <l> <supresion> <cuasi,...> <sensible>
// Entrada: <dir>/<nombre>.csv (separador ';', columna «id» + cuasi-identificadores + sensible) y
//          <dir>/jerarquia_<columna>.csv por cuasi-identificador.
// Salida:  <dir>/<nombre>_k<k>_l<l>.json con el riesgo antes, la transformación elegida y el riesgo después.
//          No guarda la tabla anonimizada (los datos de MIMIC no salen del equipo).
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
import org.deidentifier.arx.criteria.DistinctLDiversity;
import org.deidentifier.arx.criteria.KAnonymity;
import org.deidentifier.arx.risk.RiskModelSampleRisks;
import org.deidentifier.arx.risk.RiskModelSampleUniqueness;

public class ArxMedidor {

    public static void main(String[] args) throws Exception {
        File dir = new File(args[0]);
        String nombre = args[1];
        int k = Integer.parseInt(args[2]), l = Integer.parseInt(args[3]);
        double supresion = Double.parseDouble(args[4]);
        String[] cuasi = args[5].split(",");
        String sensible = args[6];

        Data data = Data.create(new File(dir, nombre + ".csv"), StandardCharsets.UTF_8, ';');
        DataDefinition def = data.getDefinition();
        def.setAttributeType("id", AttributeType.INSENSITIVE_ATTRIBUTE);
        for (String c : cuasi)
            def.setAttributeType(c, Hierarchy.create(new File(dir, "jerarquia_" + c + ".csv"), StandardCharsets.UTF_8, ';'));
        // ARX exige un modelo para todo atributo sensible: sin l-diversidad (l = 1) se declara insensible.
        def.setAttributeType(sensible, l > 1 ? AttributeType.SENSITIVE_ATTRIBUTE : AttributeType.INSENSITIVE_ATTRIBUTE);

        ARXConfiguration cfg = ARXConfiguration.create();
        cfg.addPrivacyModel(new KAnonymity(k));
        if (l > 1) cfg.addPrivacyModel(new DistinctLDiversity(sensible, l));
        cfg.setSuppressionLimit(supresion);

        Map<String, Object> m = new LinkedHashMap<>();
        m.put("datos", nombre);
        m.put("arx", ARXAnonymizer.VERSION);
        m.put("k", k);
        m.put("l", l);
        m.put("limite_supresion", supresion);
        m.put("cuasi_identificadores", String.join(",", cuasi));
        m.put("sensible", sensible);
        m.put("filas", data.getHandle().getNumRows());
        m.put("riesgo_antes", riesgos(data.getHandle()));

        long t0 = System.nanoTime();
        ARXResult res = new ARXAnonymizer().anonymize(data, cfg);
        m.put("segundos", (System.nanoTime() - t0) / 1e9);
        m.put("solucion_encontrada", res.isResultAvailable());
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
            m.put("riesgo_despues", riesgos(out));
        }
        try (PrintWriter w = new PrintWriter(new File(dir, nombre + "_k" + k + "_l" + l + ".json"), "UTF-8")) {
            w.println(json(m));
        }
        System.out.println(json(m));
    }

    // Modelo del fiscal: el atacante sabe que la persona está en los datos; riesgo = 1 / tamaño de su clase.
    static Map<String, Object> riesgos(DataHandle h) {
        RiskModelSampleRisks r = h.getRiskEstimator().getSampleBasedReidentificationRisk();
        RiskModelSampleUniqueness u = h.getRiskEstimator().getSampleBasedUniquenessRisk();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("riesgo_maximo", r.getHighestRisk());
        m.put("riesgo_promedio", r.getAverageRisk());
        m.put("fraccion_unicos", u.getFractionOfUniqueRecords());
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
