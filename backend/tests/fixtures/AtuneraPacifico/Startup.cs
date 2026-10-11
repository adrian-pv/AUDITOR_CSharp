using Microsoft.AspNetCore.Authentication.JwtBearer;

namespace AtuneraPacifico
{
    public class Startup
    {
        public void ConfigureServices(IServiceCollection services)
        {
            services.AddAuthentication().AddJwtBearer(options =>
            {
                options.RequireHttpsMetadata = false;
            });

            services.AddCors(o => o.AddPolicy("Todos", policy => policy.AllowAnyOrigin().AllowAnyHeader()));
        }
    }
}
