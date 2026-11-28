<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="ru_RU" sourcelanguage="en">
    <context>
        <name>Api</name>
        <message>
            <location filename="..\api.py" line="89" />
            <source>unavailable</source>
            <translation>недоступно</translation>
        </message>
    </context>
    <context>
        <name>Cache</name>
        <message numerus="yes">
            <location filename="..\cache.py" line="155" />
            <source>%n cached responses</source>
            <translation>
                <numerusform num="0">%n кешированный ответ</numerusform>
                <numerusform num="1">%n кешированных ответа</numerusform>
                <numerusform num="2">%n кешированных ответов</numerusform>
                <numerusform num="3">%n кешированных ответов</numerusform>
            </translation>
        </message>
        <message numerus="yes">
            <location filename="..\cache.py" line="156" />
            <source>%n cached responses, {}% of lookups served from disk</source>
            <translation>
                <numerusform num="0">%n кешированный ответ, {}% запросов обслужено с диска</numerusform>
                <numerusform num="1">%n кешированных ответа, {}% запросов обслужено с диска</numerusform>
                <numerusform num="2">%n кешированных ответов, {}% запросов обслужено с диска</numerusform>
                <numerusform num="3">%n кешированных ответов, {}% запросов обслужено с диска</numerusform>
            </translation>
        </message>
    </context>
    <context>
        <name>Dpapi</name>
        <message>
            <location filename="..\dpapi.py" line="106" />
            <source>Windows DPAPI is not available on this system, so there is nowhere safe to keep the key.</source>
            <translation>Windows DPAPI недоступна в этой системе, поэтому хранить ключ безопасно негде.</translation>
        </message>
        <message>
            <location filename="..\dpapi.py" line="118" />
            <source>Windows could not protect the key (error {}).</source>
            <translation>Windows не смогла защитить ключ (ошибка {}).</translation>
        </message>
        <message>
            <location filename="..\dpapi.py" line="121" />
            <source>Windows could not read the key (error {}).</source>
            <translation>Windows не смогла прочитать ключ (ошибка {}).</translation>
        </message>
    </context>
    <context>
        <name>NexusClient</name>
        <message>
            <location filename="..\client.py" line="70" />
            <source>Nexus rejected the key (401). Check it was copied in full.</source>
            <translation>Nexus отклонил ключ (401). Проверьте, что он скопирован целиком.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="73" />
            <source>Nexus refused the request (403).</source>
            <translation>Nexus отказал в запросе (403).</translation>
        </message>
        <message>
            <location filename="..\client.py" line="77" />
            <source>Too many requests for now (429) - wait and try again.</source>
            <translation>Слишком много запросов на сейчас (429) — подождите и попробуйте снова.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="80" />
            <source>Nexus answered {}.</source>
            <translation>Nexus ответил {}.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="88" />
            <source>Reached Nexus, but this PC could not verify its certificate ({}). That is Windows' certificate store, not the key or the connection.</source>
            <translation>До Nexus дошли, но этот компьютер не смог проверить его сертификат ({}). Это хранилище сертификатов Windows, а не проблема ключа или подключения.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="94" />
            <source>Could not reach Nexus. Check the connection.</source>
            <translation>Не удалось связаться с Nexus. Проверьте подключение.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="100" />
            <source>Nexus has no such record (404).</source>
            <translation>У Nexus нет такой записи (404).</translation>
        </message>
        <message>
            <location filename="..\client.py" line="104" />
            <source>Nexus sent something unreadable.</source>
            <translation>Nexus прислал нечитаемый ответ.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="265" />
            <source>{} Windows' own HTTPS was tried as well: {}</source>
            <translation>{} Собственный HTTPS Windows тоже пробовали: {}</translation>
        </message>
        <message>
            <location filename="..\client.py" line="280" />
            <source>Could not reach Nexus through Windows: {}.</source>
            <translation>Не удалось связаться с Nexus через Windows: {}.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="338" />
            <source>Nexus rejected the query: {}</source>
            <translation>Nexus отклонил запрос: {}</translation>
        </message>
        <message>
            <location filename="..\client.py" line="399" />
            <source>The v1 API needs a key and none is stored.</source>
            <translation>Для API v1 нужен ключ, а ни один не сохранён.</translation>
        </message>
        <message>
            <location filename="..\client.py" line="423" />
            <source>The v3 API needs a key and none is stored.</source>
            <translation>Для API v3 нужен ключ, а ни один не сохранён.</translation>
        </message>
    </context>
    <context>
        <name>NexusKeyVault</name>
        <message>
            <location filename="..\plugin.py" line="39" />
            <source>Keeps one Nexus API key, encrypted for your Windows account, and lends it to other MO2 plugins so they can use the current Nexus API instead of what MO2's built-in v1 connection hands them.</source>
            <translation>Хранит один ключ API Nexus, зашифрованный для вашей учётной записи Windows, и выдаёт его другим плагинам MO2, чтобы они пользовались актуальным API Nexus вместо того, что даёт встроенное подключение v1.</translation>
        </message>
        <message>
            <location filename="..\plugin.py" line="52" />
            <source>Nexus domain used when testing a key, e.g. skyrimspecialedition.</source>
            <translation>Домен Nexus, используемый при проверке ключа, например skyrimspecialedition.</translation>
        </message>
        <message>
            <location filename="..\plugin.py" line="58" />
            <source>Nexus API Key</source>
            <translation>Ключ API Nexus</translation>
        </message>
        <message>
            <location filename="..\plugin.py" line="61" />
            <source>Store one Nexus key for every plugin to share</source>
            <translation>Хранить один ключ Nexus для общего доступа всех плагинов</translation>
        </message>
        <message>
            <location filename="..\plugin.py" line="81" />
            <source>The vault could not be opened: {}</source>
            <translation>Хранилище не удалось открыть: {}</translation>
        </message>
    </context>
    <context>
        <name>Portable</name>
        <message>
            <location filename="..\portable.py" line="136" />
            <source>This is not a vault file written by this plugin.</source>
            <translation>Это не файл хранилища, созданный этим плагином.</translation>
        </message>
        <message>
            <location filename="..\portable.py" line="140" />
            <source>This vault file uses a scheme this version does not know about.</source>
            <translation>Этот файл хранилища использует схему, которую эта версия не знает.</translation>
        </message>
        <message>
            <location filename="..\portable.py" line="150" />
            <source>The vault file is too short to be complete.</source>
            <translation>Файл хранилища слишком короткий, чтобы быть целым.</translation>
        </message>
        <message>
            <location filename="..\portable.py" line="163" />
            <source>The vault could not be opened with this passphrase.</source>
            <translation>Хранилище нельзя открыть с этой парольной фразой.</translation>
        </message>
        <message>
            <location filename="..\portable.py" line="166" />
            <source>The vault could not be opened with this machine and install folder.</source>
            <translation>Хранилище нельзя открыть на этом компьютере и в этой папке установки.</translation>
        </message>
    </context>
    <context>
        <name>Tls</name>
        <message>
            <location filename="..\tls.py" line="39" />
            <source>MO2's Python could not load its SSL module, so it cannot make any HTTPS request. Check that libssl-3-x64.dll and libcrypto-3-x64.dll are next to ModOrganizer.exe, or reinstall MO2.</source>
            <translation>Python внутри MO2 не смог загрузить модуль SSL, поэтому не может выполнить ни один HTTPS-запрос. Проверьте, что libssl-3-x64.dll и libcrypto-3-x64.dll лежат рядом с ModOrganizer.exe, либо переустановите MO2.</translation>
        </message>
    </context>
    <context>
        <name>Vault</name>
        <message>
            <location filename="..\vault.py" line="64" />
            <source>encrypted by Windows for this user account</source>
            <translation>зашифрован Windows для этой учётной записи</translation>
        </message>
        <message>
            <location filename="..\vault.py" line="66" />
            <source>encrypted with your passphrase</source>
            <translation>зашифрован вашей парольной фразой</translation>
        </message>
        <message>
            <location filename="..\vault.py" line="67" />
            <source>obfuscated for this machine and folder - not encryption</source>
            <translation>обфусцировано для этого компьютера и папки — это не шифрование</translation>
        </message>
        <message numerus="yes">
            <location filename="..\vault.py" line="83" />
            <source>%n characters</source>
            <translation>
                <numerusform num="0">%n символ</numerusform>
                <numerusform num="1">%n символа</numerusform>
                <numerusform num="2">%n символов</numerusform>
                <numerusform num="3">%n символов</numerusform>
            </translation>
        </message>
        <message numerus="yes">
            <location filename="..\vault.py" line="84" />
            <source>%n characters, ending {}</source>
            <translation>
                <numerusform num="0">%n символ, оканчивается на {}</numerusform>
                <numerusform num="1">%n символа, оканчиваются на {}</numerusform>
                <numerusform num="2">%n символов, оканчиваются на {}</numerusform>
                <numerusform num="3">%n символов, оканчиваются на {}</numerusform>
            </translation>
        </message>
        <message>
            <location filename="..\vault.py" line="173" />
            <source>stored</source>
            <translation>сохранён</translation>
        </message>
        <message>
            <location filename="..\vault.py" line="207" />
            <source>The stored key is not readable.</source>
            <translation>Сохранённый ключ нечитаем.</translation>
        </message>
        <message>
            <location filename="..\vault.py" line="214" />
            <source>This vault is protected with a passphrase. Enter it to unlock the key.</source>
            <translation>Это хранилище защищено парольной фразой. Введите её, чтобы разблокировать ключ.</translation>
        </message>
        <message>
            <location filename="..\vault.py" line="234" />
            <source>This key was stored by Windows on another system and cannot be opened here. Remove it and enter the key again.</source>
            <translation>Этот ключ был сохранён Windows в другой системе и здесь не откроется. Удалите его и введите ключ заново.</translation>
        </message>
        <message>
            <location filename="..\vault.py" line="265" />
            <source>no key given</source>
            <translation>ключ не передан</translation>
        </message>
    </context>
    <context>
        <name>VaultDialog</name>
        <message>
            <location filename="..\ui.py" line="63" />
            <source>Your Nexus key</source>
            <translation>Ваш ключ Nexus</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="67" />
            <source>Key:</source>
            <translation>Ключ:</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="71" />
            <source>Paste a key here to store it</source>
            <translation>Вставьте ключ сюда, чтобы сохранить его</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="75" />
            <source>Show what I am typing</source>
            <translation>Показывать ввод</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="83" />
            <source>Protect with a passphrase:</source>
            <translation>Защитить парольной фразой:</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="98" />
            <source>Save</source>
            <translation>Сохранить</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="99" />
            <source>Test</source>
            <translation>Проверить</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="100" />
            <source>Unlock</source>
            <translation>Разблокировать</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="101" />
            <source>Remove stored key</source>
            <translation>Удалить сохранённый ключ</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="108" />
            <source>Get one from nexusmods.com -&gt; your profile -&gt; Site preferences -&gt; API keys.

It is written to the vault's own file, not to ModOrganizer.ini, where plugin settings are kept in plain text.</source>
            <translation>Получите его на nexusmods.com -&gt; ваш профиль -&gt; Site preferences -&gt; API keys.

Он записывается в собственный файл хранилища, а не в ModOrganizer.ini, где настройки плагинов лежат открытым текстом.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="120" />
            <source>Running under Wine, where there is no OS secret to borrow. Without a passphrase the key is only obfuscated: tied to this machine and folder, so a copied file is useless - but readable in place by anything that can read this plugin's source. A passphrase is the only real protection here, and is asked for once per session.</source>
            <translation>Работа под Wine, где нет системного секрета, который можно позаимствовать. Без парольной фразы ключ лишь обфусцирован: привязан к этому компьютеру и папке, так что скопированный файл бесполезен — но на месте его может прочитать всё, что способно прочитать исходники плагина. Парольная фраза — единственная настоящая защита здесь, и запрашивается она раз за сессию.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="128" />
            <source>The key is encrypted with your passphrase. Nothing on this disk can open it without that, and if you forget it the key is gone - generate a new one on Nexus.</source>
            <translation>Ключ зашифрован вашей парольной фразой. Ничто на этом диске не откроет его без неё, а если вы её забудете — ключ потерян: сгенерируйте новый на Nexus.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="133" />
            <source>Windows encrypts the key for this user account. A passphrase is optional here, and protects it even from someone who has your unlocked Windows account.</source>
            <translation>Windows шифрует ключ для этой учётной записи. Парольная фраза здесь необязательна и защищает ключ даже от того, кто имеет доступ к вашей разблокированной учётной записи Windows.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="142" />
            <source>Your key was stored by an earlier version through Wine's version of Windows encryption, which looks like encryption but is openable by anyone holding the file.

It has been re-stored under this version's scheme. If that file was ever backed up, shared or put in a support archive, treat the key as exposed and generate a new one on Nexus.</source>
            <translation>Ваш ключ был сохранён ранней версией через винную реализацию шифрования Windows: выглядит как шифрование, но открывается любым владельцем файла.

Ключ пересохранён по схеме этой версии. Если этот файл когда-либо попадал в резервную копию, пересылался или прикладывался к архиву поддержки — считайте ключ скомпрометированным и сгенерируйте новый на Nexus.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="150" />
            <source>No key stored. Plugins asking for one are being told there is none, and are expected to carry on without it.</source>
            <translation>Ключ не сохранён. Обращающимся плагинам сообщают, что ключа нет, и предполагается, что они продолжат работу без него.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="155" />
            <source>A key is stored, protected with a passphrase. Type it above and press Unlock to make it available to plugins for this session.</source>
            <translation>Ключ сохранён и защищён парольной фразой. Введите её выше и нажмите «Разблокировать», чтобы сделать ключ доступным плагинам в этой сессии.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="161" />
            <source>A key is stored ({}), {}.</source>
            <translation>Ключ сохранён ({}), {}.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="165" />
            <source>There is a key here that cannot be opened on this system - most likely the file came from another machine, account or folder. Remove it and paste the key again. ({})</source>
            <translation>Здесь лежит ключ, который нельзя открыть в этой системе — скорее всего, файл пришёл с другого компьютера, учётной записи или из другой папки. Удалите его и вставьте ключ заново. ({})</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="175" />
            <source>Nothing is waiting on a passphrase.</source>
            <translation>Парольная фраза сейчас никого не ждёт.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="180" />
            <source>Type the passphrase first.</source>
            <translation>Сначала введите парольную фразу.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="195" />
            <source>Nothing was typed, so nothing has changed.</source>
            <translation>Ничего не введено, значит ничего не изменилось.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="200" />
            <source>Type a passphrase, or clear the checkbox to store without one.</source>
            <translation>Введите парольную фразу или снимите галочку, чтобы сохранить без неё.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="208" />
            <source>Not stored: {}</source>
            <translation>Не сохранено: {}</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="213" />
            <source>Stored ({}), {}.</source>
            <translation>Сохранено ({}), {}.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="224" />
            <source>Nothing to test - the box is empty and no key is stored.</source>
            <translation>Проверять нечего — поле пусто и ключ не сохранён.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="227" />
            <source>Checking...</source>
            <translation>Проверяю...</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="234" />
            <source>That key did not work: {}</source>
            <translation>Этот ключ не сработал: {}</translation>
        </message>
        <message numerus="yes">
            <location filename="..\ui.py" line="236" />
            <source>Works - Nexus returned %n categories for {} over v1. The same key reaches v3; v2's public queries need none.</source>
            <translation>
                <numerusform num="0">Работает — Nexus вернул %n категорию для {} через v1. Тем же ключом доступен v3; публичным запросам v2 ключ не нужен.</numerusform>
                <numerusform num="1">Работает — Nexus вернул %n категории для {} через v1. Тем же ключом доступен v3; публичным запросам v2 ключ не нужен.</numerusform>
                <numerusform num="2">Работает — Nexus вернул %n категорий для {} через v1. Тем же ключом доступен v3; публичным запросам v2 ключ не нужен.</numerusform>
                <numerusform num="3">Работает — Nexus вернул %n категорий для {} через v1. Тем же ключом доступен v3; публичным запросам v2 ключ не нужен.</numerusform>
            </translation>
        </message>
        <message>
            <location filename="..\ui.py" line="246" />
            <source>Remove the stored key? Plugins asking for one will be told there is none.</source>
            <translation>Удалить сохранённый ключ? Обращающимся плагинам будут сообщать, что ключа нет.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="258" />
            <source>Plugins that have asked for it</source>
            <translation>Плагины, запрашивавшие ключ</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="260" />
            <source>Every plugin runs inside MO2 as you do, so this list is a record rather than a lock: a plugin determined to read the key would not have to ask. Denying one stops any plugin using the published way in.</source>
            <translation>Каждый плагин работает внутри MO2 с вашими же правами, поэтому этот список — скорее журнал, чем замок: плагин, твёрдо решивший прочитать ключ, спрашивать не обязан. Запрет лишает плагин официального пути к ключу.</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="268" />
            <source>Plugin</source>
            <translation>Плагин</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="268" />
            <source>Times asked</source>
            <translation>Запросов</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="269" />
            <source>Last asked</source>
            <translation>Последний запрос</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="269" />
            <source>Allowed</source>
            <translation>Разрешено</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="277" />
            <source>Allow</source>
            <translation>Разрешить</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="278" />
            <source>Deny</source>
            <translation>Запретить</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="279" />
            <source>Forget</source>
            <translation>Забыть</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="292" />
            <source>yes</source>
            <translation>да</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="292" />
            <source>NO</source>
            <translation>НЕТ</translation>
        </message>
        <message>
            <location filename="..\ui.py" line="332" />
            <source>These plugins keep a Nexus key of their own in plain text in ModOrganizer.ini: {}.

The ini is not encrypted, so that copy can be read by anything that can read the file - including anyone you send an instance backup to.

Move it into the vault and blank the plain-text copy?

This touches only those plugins' own settings. MO2's own Nexus login is stored separately and is not affected: downloads, endorsements and update checks keep working.</source>
            <translation>Эти плагины хранят собственный ключ Nexus открытым текстом в ModOrganizer.ini: {}.

ini не зашифрован, поэтому эту копию может прочитать всё, что способно прочитать файл — включая того, кому вы отправите резервную копию экземпляра.

Перенести ключ в хранилище и затереть открытую копию?

Это касается только собственных настроек этих плагинов. Собственный вход MO2 в Nexus хранится отдельно и не затрагивается: загрузки, одобрения и проверки обновлений продолжат работать.</translation>
        </message>
        <message numerus="yes">
            <location filename="..\ui.py" line="359" />
            <source>%n key(s) taken into the vault.</source>
            <translation>
                <numerusform num="0">В хранилище принят %n ключ.</numerusform>
                <numerusform num="1">В хранилище принято %n ключа.</numerusform>
                <numerusform num="2">В хранилище принято %n ключей.</numerusform>
                <numerusform num="3">В хранилище принято %n ключей.</numerusform>
            </translation>
        </message>
        <message numerus="yes">
            <location filename="..\ui.py" line="360" />
            <source>%n plain-text copy(ies) blanked.</source>
            <translation>
                <numerusform num="0">Затёрт %n открытый текстовый экземпляр.</numerusform>
                <numerusform num="1">Затёрто %n открытых текстовых экземпляра.</numerusform>
                <numerusform num="2">Затёрто %n открытых текстовых экземпляров.</numerusform>
                <numerusform num="3">Затёрто %n открытых текстовых экземпляров.</numerusform>
            </translation>
        </message>
        <message>
            <location filename="..\ui.py" line="361" />
            <source>MO2 rewrites its ini on exit, so the old value may still be visible in the file until you close MO2.</source>
            <translation>MO2 перезаписывает ini при выходе, поэтому старое значение может оставаться видимым в файле, пока MO2 не закрыт.</translation>
        </message>
    </context>
    <context>
        <name>WinHttp</name>
        <message>
            <location filename="..\winhttp.py" line="41" />
            <source>the request timed out</source>
            <translation>истекло время ожидания запроса</translation>
        </message>
        <message>
            <location filename="..\winhttp.py" line="42" />
            <source>the server name could not be resolved</source>
            <translation>имя сервера не удалось разрешить</translation>
        </message>
        <message>
            <location filename="..\winhttp.py" line="44" />
            <source>the connection could not be made</source>
            <translation>соединение не удалось установить</translation>
        </message>
        <message>
            <location filename="..\winhttp.py" line="45" />
            <source>the connection was dropped</source>
            <translation>соединение оборвалось</translation>
        </message>
        <message>
            <location filename="..\winhttp.py" line="46" />
            <source>the server sent an invalid response</source>
            <translation>сервер прислал недопустимый ответ</translation>
        </message>
        <message>
            <location filename="..\winhttp.py" line="48" />
            <source>Windows rejected the server's certificate</source>
            <translation>Windows отклонила сертификат сервера</translation>
        </message>
        <message>
            <location filename="..\winhttp.py" line="60" />
            <source>Windows error {}</source>
            <translation>Ошибка Windows {}</translation>
        </message>
    </context>
</TS>
