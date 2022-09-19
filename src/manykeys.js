/*!

ManyKeys.js v1.0.0 - The JavaScript library to make your frontend application compatible with manykeys

(c) Adrian Steffan <adrian.steffan [at] hotmail.de> <https://github.com/adriansteffan>
(c) Till Müller <https://github.com/TillMueller>
Licenced under GPLv3. See https://raw.githubusercontent.com/adriansteffan/manykeys/main/LICENSE
*/

const ManyKeys = {

    /**
     * Extracts the RSA public key and username from the provided keystring. Alerts the user if the key is invalid.
     * @param  {String} publicKeyString The keystring generated by the ManyKeys python script
     * @return {{String, String}} An object containing the username and key
     */

    verifyAndReadKeystring: function(publicKeyString){
        // Add = padding from the "truly" urlsafe b64
        publicKeyStringPadded = publicKeyString + "=".repeat((4 - (publicKeyString.length % 4))%4);
            
        data = window.atob(publicKeyStringPadded.replace(/_/g, '/').replace(/-/g, '+'));
        var checksum = data.substring(0,32);
        var content = data.substring(32);

        const verifyChecksum =  async function(text, checksum) {
            
            const checkSumArray = Uint8Array.from(checksum, c => c.charCodeAt(0));
    
            const msgUint8 = new TextEncoder().encode(text);
            const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            
            for(var i = 0; i<hashArray.length;i++){
                if(hashArray[i] !== checkSumArray[i]){
                    return false;
                }
            }
            return true; 
        }

        verifyChecksum(content, checksum).then(success => {if(!success){alert("Keyformat Invalid! Please request a new link")}});

        var DELIMITER = ";"
        var key = content.substr(0,content.indexOf(DELIMITER));
        var username = content.substr(content.indexOf(DELIMITER)+1);

        return {key, username};
    },


    /**
     * Asymmetrically encrypts the plaintext bytes to match to be decipherable by the ManyKeys python script  
     * @param  {Uint8Array}  The bytes of data to be encrypted
     * @param  {string} num2 The public asymmetrical encryption key taken from the keystring
     * @return {Promise.string} A base64 encoded string representation of (asymm-encrypted aes-key + sym-encrypted data)
     */
    encrypt: async function(plaintext, key){

        var sessionkey = await window.crypto.getRandomValues(new Uint8Array(32));
        const sessionkey_encoded = await crypto.subtle.importKey("raw", sessionkey.buffer, 'AES-GCM', false, ["encrypt", "decrypt"]);

        // from https://developers.google.com/web/updates/2012/06/How-to-convert-ArrayBuffer-to-and-from-String
        function str2ab(str) {
            const buf = new ArrayBuffer(str.length);
            const bufView = new Uint8Array(buf);
            for (let i = 0, strLen = str.length; i < strLen; i++) {
            bufView[i] = str.charCodeAt(i);
            }
            return buf;
        }

        // fetch the part of the PEM string between header and footer
        const pemHeader = "-----BEGIN PUBLIC KEY-----";
        const pemFooter = "-----END PUBLIC KEY-----";
        const pemContents = key.substring(pemHeader.length, key.length - pemFooter.length);
        // base64 decode the string to get the binary data
        const binaryDerString = window.atob(pemContents);
        // convert from a binary string to an ArrayBuffer
        const binaryDer = str2ab(binaryDerString);
        const key_encoded = await crypto.subtle.importKey("spki", binaryDer, {name: 'RSA-OAEP', hash: 'SHA-256'}, false, ["encrypt"]);

        // Encrypt the session key with the public RSA key
        var encSessKey = await window.crypto.subtle.encrypt(
            {
            name: "RSA-OAEP"
            },
            key_encoded,
            sessionkey
        );
        
        // Encrypt the data with the AES session key
        // iv will be needed for decryption
        const iv = await window.crypto.getRandomValues(new Uint8Array(16));

        var ciphertextAndTag = await window.crypto.subtle.encrypt(
            {
            name: "AES-GCM",
            iv: iv,
            tagLength: 128,
            },
            sessionkey_encoded,
            plaintext
        );

        const encSessKeyArray = new Uint8Array(encSessKey);
        const ciphertextAndTagArray = new Uint8Array(ciphertextAndTag);

        uint8stream = new Int8Array(encSessKeyArray.length + iv.length + ciphertextAndTagArray.length);
        uint8stream.set(encSessKeyArray);
        uint8stream.set(iv, encSessKeyArray.length);
        uint8stream.set(ciphertextAndTagArray, encSessKeyArray.length + iv.length);
        
        return new Promise ((resolve, reject) => {
            var b64converter = new FileReader();
        
            b64converter.onloadend = function (event) {
                resolve(b64converter.result.split(",")[1]);
            }

            b64converter.readAsDataURL(new Blob([uint8stream])); 
        });     
    }
}
