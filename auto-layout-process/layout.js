const { layoutProcess } = require("yet-another-bpmn-auto-layout");

const main = async () => {
  let bpmnXml = "";

  // Lê o XML do stdin enviado pelo Python
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    bpmnXml += chunk;
  }

  if (!bpmnXml.trim()) {
    process.stderr.write("Erro: nenhum XML recebido via stdin.\n");
    process.exit(1);
  }

  try {
    const layoutedXml = await layoutProcess(bpmnXml);
    process.stdout.write(layoutedXml);
  } catch (error) {
    process.stderr.write(`Erro ao processar BPMN XML: ${error.stack}\n`);
    process.exit(1);
  }
};

main();
