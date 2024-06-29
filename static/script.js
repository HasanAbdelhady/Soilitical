function generateRandomValuesAndSubmit() {
  // Generate random values within specified ranges
  var nValue = Math.floor(Math.random() * (250 - 15 + 1)) + 15;
  var pValue = Math.floor(Math.random() * (250 - 15 + 1)) + 15;
  var kValue = Math.floor(Math.random() * (250 - 15 + 1)) + 15;
  var phValue = Math.random() * (14 - 1) + 1;
  var humidityValue = Math.floor(Math.random() * (100 - 1 + 1)) + 1;
  var temperatureValue = Math.floor(Math.random() * (65 - 0 + 1));
  var rainfallValue = Math.floor(Math.random() * (2600 - 1 + 1)) + 1;

  // Set the random values to the form fields
  document.getElementById("n_value").value = nValue;
  document.getElementById("p_value").value = pValue;
  document.getElementById("k_value").value = kValue;
  document.getElementById("ph_values").value = phValue.toFixed(2); // Round to 2 decimal places
  document.getElementById("humidity").value = humidityValue;
  document.getElementById("temperature").value = temperatureValue;
  document.getElementById("rainfall").value = rainfallValue;
}
