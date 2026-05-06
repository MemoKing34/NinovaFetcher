# Ninona Fetcher

`NinovaFetcher` İTÜ Ninova platformundan dosya indirme işlemini kolaylaştırmak için hazırlanmış bir programdır.

## Kullanım

### Windows kolay kurulum

Windows kullanıcıları aşağıdaki tek komut ile hem Python hem de Git'i yükleyip `NinovaFetcher`'ı kullanabilirler. Skript size `NinovaFetcher`'ı hangi klasöre kurmak isteyeceğinizi soracak. (Varsayılan Belgelerim klasörü). Daha sonra `NinovaFetcher`'ı ve dosyalarınızı o klasörde bulabilirsiniz.

```pwsh
irm https://raw.githubusercontent.com/MemoKing34/NinovaFetcher/refs/heads/master/Install.ps1 | iex
```

> [!INFO]
> Eğer bu komutu nasıl çalıştıracağınız hakkında fikriniz yok ise windows logosuna sağ tıklayın ve "Terminal" seçeneğine tıklayın. Ardından karşınıza gelen siyah kutuya bu komutu yapıştırın ve entere basın. Gerisini okuyarak yapabilirsiniz :)

### Manuel kurulum

> [!NOTE]
> Programı çalıştırmak için sisteminizde python yüklü olması gerekmektedir. [python.org](https://python.org) sitesinden indirebilirsiniz.


İster git ile isterseniz de zip olarak programı indirin. Eğer Windows kullanıyorsanız `run.bat` adlı dosyayı Linux/MacOS kullanıyorsanız ise terminalden `run.sh` dosyasını çalıştırın. Program gerekli bilgileri ilk çalışmasında soracaktır. Program çalıştıktan sonra `downloads` klasöründe tüm ninova dosyalarınızı yüklü bir şekilde göreceksiniz.