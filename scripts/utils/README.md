# Utility Scripts

Shared utility modules and helper functions for the MeatWise API.

## Modules

### supabase_client.py
Supabase client configuration:
- Connection management
- Authentication setup
- Error handling
- Retry logic

## Common Functions

### Database Utilities
- Connection pooling
- Transaction management
- Error handling
- Query builders

### Image Processing
- Image validation
- Format conversion
- Size optimization
- Error handling

### API Helpers
- Rate limiting
- Request retries
- Response parsing
- Error handling

## Usage

1. **Import Supabase Client**
   ```python
   from utils.supabase_client import get_supabase
   
   client = get_supabase()
   ```

2. **Use Database Utils**
   ```python
   from utils.db import get_connection_pool
   
   pool = await get_connection_pool()
   ```

## Best Practices

1. **Code Organization**
   - Keep utils focused
   - Document all functions
   - Use type hints
   - Follow PEP 8

2. **Error Handling**
   - Use custom exceptions
   - Provide context
   - Log appropriately
   - Clean up resources

3. **Performance**
   - Cache when possible
   - Optimize imports
   - Use async where appropriate
   - Monitor resource usage

## Development Guidelines

1. **Adding New Utils**
   - Keep functions generic
   - Add proper documentation
   - Include type hints
   - Write unit tests

2. **Modifying Existing Utils**
   - Maintain compatibility
   - Update documentation
   - Add deprecation notices
   - Test thoroughly

3. **Dependencies**
   - Minimize external deps
   - Version pin carefully
   - Document requirements
   - Check for conflicts 