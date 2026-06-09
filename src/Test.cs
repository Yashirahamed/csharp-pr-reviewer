using System;
using System.Data.SqlClient;
using System.Threading.Tasks;

namespace EnterpriseApp.Services
{
    public class PaymentProcessor
    {
        // 1. Security Violation: Hardcoded database credentials in connection string
        private readonly string _connectionString = "Server=myServerAddress;Database=myDataBase;User Id=myUsername;Password=myPassword123;";

        // 2. SOLID DIP Violation: Direct instantiation of concrete dependency instead of using Dependency Injection
        private readonly FileLogger _logger = new FileLogger();

        public async Task<bool> ProcessPaymentAsync(string userId, decimal amount, string currency)
        {
            // 3. Nullability Violation: Lack of argument null validation (userId and currency could be null)
            _logger.Log($"Processing payment of {amount} {currency} for user {userId}");

            // 4. Security Violation: SQL Injection vulnerability via string interpolation in raw SQL query
            string query = $"SELECT * FROM Users WHERE UserId = '{userId}' AND IsActive = 1";

            using (var connection = new SqlConnection(_connectionString))
            {
                await connection.OpenAsync();
                using (var command = new SqlCommand(query, connection))
                {
                    // 5. Nullability Violation: Potential NullReferenceException if ExecuteScalar returns null
                    var userStatus = command.ExecuteScalar();
                    if (userStatus.ToString() == "Inactive")
                    {
                        return false;
                    }
                }
            }

            // 6. Async/Await Violation: Blocking async call using '.Result' (sync-over-async), risking thread starvation
            bool isBlacklisted = CheckBlacklistAsync(userId).Result; 
            if (isBlacklisted)
            {
                return false;
            }

            return true;
        }

        private async Task<bool> CheckBlacklistAsync(string userId)
        {
            await Task.Delay(100); // Simulate check network delay
            return false;
        }
    }

    public class FileLogger
    {
        public void Log(string message)
        {
            Console.WriteLine(message);
        }
    }
}
