const fs = require('fs');
const path = require('path');

// Helper to escape CSV fields
function escapeCSV(val) {
    if (val === null || val === undefined) return '';
    let str = Array.isArray(val) ? val.join('; ') : String(val);
    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
        str = '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
}

function processData() {
    const jsonPath = path.join(__dirname, 'dashboard_data.json');
    console.log('Leyendo dashboard_data.json...');
    let content = fs.readFileSync(jsonPath, 'utf8');

    // Reparar posibles concatenaciones o cortes si existieran
    content = content.replace(/\s*\]\s*\}idad":/g, ',\n    {\n      "Cantidad":');

    let data;
    try {
        data = JSON.parse(content);
        console.log('JSON parseado correctamente.');
    } catch (err) {
        console.error('Error parseando JSON:', err.message);
        process.exit(1);
    }

    // Ordenar fechas cronológicamente (ISO YYYY-MM-DD)
    const rawDates = data.dates || [];
    const indexedDates = rawDates.map((d, idx) => ({ date: d, origIdx: idx }));
    indexedDates.sort((a, b) => a.date.localeCompare(b.date));

    const sortedDates = indexedDates.map(item => item.date);
    const sortedBranches = {};

    if (data.branches) {
        Object.keys(data.branches).forEach(branch => {
            const origArr = data.branches[branch];
            sortedBranches[branch] = indexedDates.map(item => origArr[item.origIdx] || 0);
        });
    }

    // 1. Generar dashboard_resumen.json (Ordenado cronológicamente)
    const resumen = {
        dates: sortedDates,
        branches: sortedBranches
    };
    const resumenPath = path.join(__dirname, 'dashboard_resumen.json');
    fs.writeFileSync(resumenPath, JSON.stringify(resumen, null, 2), 'utf8');
    console.log(`dashboard_resumen.json generado exitosamente (${(fs.statSync(resumenPath).size / 1024).toFixed(2)} KB, ${sortedDates.length} fechas ordenadas).`);

    // 2. Generar productos.csv (Incluye categoria y subcategoria)
    const csvPath = path.join(__dirname, 'productos.csv');
    const header = 'Sucursal,Fecha,Descripcion,Cantidad,Total,proveedor,categoria,subcategoria\n';
    const products = data.products || [];

    const rows = products.map(p => {
        return [
            escapeCSV(p.Sucursal),
            escapeCSV(p.Fecha),
            escapeCSV(p.Descripcion),
            p.Cantidad !== undefined ? p.Cantidad : 0,
            p.Total !== undefined ? p.Total : 0,
            escapeCSV(p.proveedor),
            escapeCSV(p.categoria || 'Otros'),
            escapeCSV(p.subcategoria || 'Otros')
        ].join(',');
    });

    fs.writeFileSync(csvPath, header + rows.join('\n'), 'utf8');
    console.log(`productos.csv generado exitosamente (${(fs.statSync(csvPath).size / 1024 / 1024).toFixed(2)} MB, ${products.length} registros).`);
}

processData();
