using Microsoft.AspNetCore.Mvc;

namespace AtuneraPacifico.Controllers
{
    public class AuthController : Controller
    {
        private const string AdminPassword = "pruebas21_SecretPassword_2026";
        private readonly ILogger<AuthController> _logger;

        [HttpPost]
        public IActionResult Login(string usuario, string password)
        {
            _logger.LogInformation("Intento de login de " + usuario + " con clave " + password);
            if (password == AdminPassword)
            {
                return Ok();
            }
            return Unauthorized();
        }
    }
}
