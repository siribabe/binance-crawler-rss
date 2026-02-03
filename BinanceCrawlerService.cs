using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace BlockchainNews.Services
{
    public class BinanceCrawlerService : IHostedService, IDisposable
    {
        private readonly ILogger<BinanceCrawlerService> _logger;
        private Timer _timer;
        
        // 定时间隔：2小时（可根据需要调整）
        private readonly TimeSpan _interval = TimeSpan.FromHours(2);


        public BinanceCrawlerService(ILogger<BinanceCrawlerService> logger)
        {
            _logger = logger;
        }

        public Task StartAsync(CancellationToken cancellationToken)
        {
            _logger.LogInformation("BinanceCrawlerService 启动");

            // 启动后立即执行一次，然后按间隔定时执行
            _timer = new Timer(ExecuteCrawler, null, TimeSpan.Zero, _interval);

            return Task.CompletedTask;
        }

        private void ExecuteCrawler(object state)
        {
            // 执行 binance blog 爬虫
            ExecutePythonScript("binance", "main.py");
            
            // 执行 binance_detail 爬虫
            ExecutePythonScript("binance_detail", "main.py");
        }

        private void ExecutePythonScript(string crawlerFolder, string scriptName)
        {
            try
            {
                _logger.LogInformation($"开始执行 {crawlerFolder} 爬虫...");

                var baseDir = AppDomain.CurrentDomain.BaseDirectory;
                var scriptPath = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "Crawler", crawlerFolder, scriptName));
                var workingDir = Path.GetDirectoryName(scriptPath);

                // 发布后路径可能不同
                if (!File.Exists(scriptPath))
                {
                    scriptPath = Path.Combine(baseDir, "Crawler", crawlerFolder, scriptName);
                    workingDir = Path.GetDirectoryName(scriptPath);
                }

                if (!File.Exists(scriptPath))
                {
                    _logger.LogError($"找不到爬虫脚本: {scriptPath}");
                    return;
                }

                var processInfo = new ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = $"\"{scriptPath}\"",
                    WorkingDirectory = workingDir,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using (var process = Process.Start(processInfo))
                {
                    var output = process.StandardOutput.ReadToEnd();
                    var error = process.StandardError.ReadToEnd();
                    process.WaitForExit();

                    if (process.ExitCode == 0)
                    {
                        _logger.LogInformation($"{crawlerFolder} 爬虫执行成功\n{output}");
                    }
                    else
                    {
                        _logger.LogError($"{crawlerFolder} 爬虫执行失败，退出码: {process.ExitCode}\n{error}");
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"执行 {crawlerFolder} 爬虫时发生异常");
            }
        }
        public Task StopAsync(CancellationToken cancellationToken)
        {
            _logger.LogInformation("BinanceCrawlerService 停止");
            _timer?.Change(Timeout.Infinite, 0);
            return Task.CompletedTask;
        }

        public void Dispose()
        {
            _timer?.Dispose();
        }
    }
}