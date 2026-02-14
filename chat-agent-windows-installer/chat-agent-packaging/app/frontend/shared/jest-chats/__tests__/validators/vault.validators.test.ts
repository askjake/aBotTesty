import {
  setupVaultValidator,
  updateVaultPasswordValidator,
  passwordSchema,
} from '@/validators/vault.validators';

describe('passwordSchema', () => {
  it('validates a password with valid length, characters, and requirements', () => {
    const validPassword = 'ValidP@ssw0rd';

    const result = passwordSchema.safeParse(validPassword);
    expect(result.success).toBe(true);
  });

  it('rejects a password that is too short', () => {
    const invalidPassword = 'Short';

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must be at least 8 characters long',
    );
  });

  it('rejects a password that is too long', () => {
    const invalidPassword = 'a'.repeat(33);

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must not exceed 32 characters',
    );
  });

  it('rejects a password that doesnt contains one number', () => {
    const invalidPassword = 'InvalidPassword!';

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must contain at least one number',
    );
  });
  it('rejects a password that does not contain a lowercase letter', () => {
    const invalidPassword = 'INVALIDPASS1!';

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must contain at least one lowercase letter',
    );
  });

  it('rejects a password that does not contain an uppercase letter', () => {
    const invalidPassword = 'validpass1!';

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must contain at least one uppercase letter',
    );
  });

  it('rejects a password that does not contain a number', () => {
    const invalidPassword = 'ValidPass!';

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must contain at least one number',
    );
  });

  it('rejects a password that does not contain a special character', () => {
    const invalidPassword = 'ValidPass1';

    const result = passwordSchema.safeParse(invalidPassword);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must contain at least one special character',
    );
  });
});

describe('setupVaultValidator', () => {
  it('validates a vault setup with a valid password', () => {
    const validSetup = {
      password: 'ValidP@ssw0rd',
    };

    const result = setupVaultValidator.safeParse(validSetup);
    expect(result.success).toBe(true);
    expect(result.data).toEqual(validSetup);
  });

  it('rejects a vault setup with an invalid password', () => {
    const invalidSetup = {
      password: 'Short',
    };

    const result = setupVaultValidator.safeParse(invalidSetup);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must be at least 8 characters long',
    );
  });

  it('rejects a vault setup without the password field', () => {
    const invalidSetup = {};

    const result = setupVaultValidator.safeParse(invalidSetup);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Invalid input: expected string, received undefined',
    );
  });
});

describe('updateVaultPasswordValidator', () => {
  it('validates a vault password update with valid old and new passwords', () => {
    const validUpdate = {
      oldPassword: 'OldP@ssw0rd',
      newPassword: 'NewP@ssw0rd',
    };

    const result = updateVaultPasswordValidator.safeParse(validUpdate);
    expect(result.success).toBe(true);
    expect(result.data).toEqual(validUpdate);
  });

  it('rejects a vault password update with an invalid old password', () => {
    const invalidUpdate = {
      oldPassword: 'Short',
      newPassword: 'NewP@ssw0rd',
    };

    const result = updateVaultPasswordValidator.safeParse(invalidUpdate);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must be at least 8 characters long',
    );
  });

  it('rejects a vault password update with an invalid new password', () => {
    const invalidUpdate = {
      oldPassword: 'OldP@ssw0rd',
      newPassword: 'Short',
    };

    const result = updateVaultPasswordValidator.safeParse(invalidUpdate);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Passphrase must be at least 8 characters long',
    );
  });

  it('rejects a vault password update with the same old and new passwords', () => {
    const invalidUpdate = {
      oldPassword: 'OldP@ssw0rd',
      newPassword: 'OldP@ssw0rd',
    };

    const result = updateVaultPasswordValidator.safeParse(invalidUpdate);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'New password must be different from current password',
    );
  });

  it('rejects a vault password update without the oldPassword field', () => {
    const invalidUpdate = {
      newPassword: 'NewP@ssw0rd',
    };

    const result = updateVaultPasswordValidator.safeParse(invalidUpdate);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Invalid input: expected string, received undefined',
    );
  });

  it('rejects a vault password update without the newPassword field', () => {
    const invalidUpdate = {
      oldPassword: 'OldP@ssw0rd',
    };

    const result = updateVaultPasswordValidator.safeParse(invalidUpdate);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'Invalid input: expected string, received undefined',
    );
  });
});
