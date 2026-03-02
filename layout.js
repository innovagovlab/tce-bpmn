const { layoutProcess } = require('bpmn-auto-layout');

let bpmnXml = `
XML usado (tô fazendo manualmente por agora)
`;

async function layoutBpmnXml(bpmnXml) {
    try {
        return await layoutProcess(bpmnXml);
    } catch (error) {
        console.error('Error processing BPMN XML:', error);
        return null;
    }
}

// Exemplo feito do paper
layoutBpmnXml(bpmnXml).then((layoutedXml) => {
    console.log(layoutedXml);
});