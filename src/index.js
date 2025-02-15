import axios from 'axios';
import fs from 'fs';
import path from 'path';
import 'dotenv/config';

const API_URL = "https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/";

async function sendRequest(endpoint, payload, apiKey = null) {
    try {
        const headers = apiKey ? { 'X-Auth-Token': apiKey } : {};
        const response = await axios.post(`${API_URL}${endpoint}?jsonRequest=${JSON.stringify(payload)}`, {}, { headers });
        if (response.data.errorCode) {
            throw new Error(`${response.data.errorCode}: ${response.data.error}`);
        }
        console.log(`✅ Finished request ${endpoint}`);
        return response.data.data;
    } catch (error) {
        console.error(`❌ Request to ${endpoint} failed:`, error.response ? error.response.data : error.message);
        return null;
    }
}

async function authenticate(username, password, catalogId) {
    return sendRequest("login", { username, password, authType: "EROS", catalogId });
}

async function logout(apiKey) {
    return sendRequest("logout", { apiKey });
}

async function searchScenes(apiKey, datasetName, pathRowList, startDate, endDate, maxResults) {
    const additionalCriteria = {
        filterType: "or",
        childFilters: pathRowList.map(([path, row]) => ({
            filterType: "and",
            childFilters: [
                { filterType: "value", fieldId: 10036, value: `${path}`, operand: "=" },
                { filterType: "value", fieldId: 10038, value: `${row}`, operand: "=" }
            ]
        }))
    };

    return sendRequest("search", {
        datasetName,
        temporalFilter: { dateField: "search_date", startDate, endDate },
        maxResults,
        additionalCriteria,
        node: "EE",
        apiKey
    });
}

async function getDownloadList(apiKey, datasetName, entityIds) {
    return sendRequest("download", {
        datasetName,
        entityIds,
        products: ["STANDARD"],
        node: "EE",
        apiKey
    });
}

async function downloadFile(url, filePath) {
    const writer = fs.createWriteStream(filePath);
    const response = await axios({ url, method: 'GET', responseType: 'stream' });
    response.data.pipe(writer);
    return new Promise((resolve, reject) => {
        writer.on("finish", () => resolve());
        writer.on("error", reject);
    });
}

async function main() {
    const username = process.env.USGS_USERNAME;
    const password = process.env.USGS_PASSWORD;
    const catalogId = "EE";

    const apiKey = await authenticate(username, password, catalogId);
    if (!apiKey) return;

    const datasets = ["LANDSAT_8_C1"];
    const pathRowList = [[165, 14], [166, 14]];
    const startDate = "2016-05-01T00:00:00Z";
    const endDate = "2100-01-01T00:00:00Z";
    const maxResults = 10;

    for (const dataset of datasets) {
        const scenes = await searchScenes(apiKey, dataset, pathRowList, startDate, endDate, maxResults);
        if (!scenes || scenes.length === 0) {
            console.log("⚠️ No scenes found.");
            continue;
        }

        const entityIds = scenes.map(scene => scene.entityId);
        const downloads = await getDownloadList(apiKey, dataset, entityIds);
        if (!downloads || downloads.length === 0) {
            console.log("⚠️ No available downloads.");
            continue;
        }

        for (const download of downloads) {
            const filePath = path.join("./downloads", `${download.entityId}.tar.gz`);
            console.log(`⬇️ Downloading ${filePath}...`);
            await downloadFile(download.url, filePath);
            console.log(`✅ Downloaded: ${filePath}`);
        }
    }

    await logout(apiKey);
    console.log("✅ All downloads complete.");
}

main();
